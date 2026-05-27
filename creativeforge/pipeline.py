"""Pipeline orchestration.

Iterates stages in dependency order, dispatches each item to the configured
adapter (image / video / voice / audio search / compose), and persists progress
to `runs/<id>/state.json` so `resume` can pick up later.

Stage directory layout:

    runs/<id>/
        state.json
        stage-00-character-sheets/
            <item>.png
            <item>.meta.json
        stage-01-cut-images/
        stage-02-cut-videos/
        stage-03-voice/
        stage-04-audio/
        stage-05-compose/
        prompt-overrides/   (created by ui/approve.py on [e])
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from rich.console import Console
from ruamel.yaml import YAML

from creativeforge.adapters.base import GenRequest, GenResult, get_adapter
from creativeforge.browser.selectors import CURRENT_RUN_DIR
from creativeforge.config import ProjectConfig, StageSpec
from creativeforge.state import RunState

yaml = YAML(typ="safe")
console = Console()


# Adapter kind classification by registered name. New adapters need an entry here.
ADAPTER_KIND: dict[str, str] = {
    "google_flow_imagen": "image",
    "google_flow_veo": "video",
    "edge_tts": "voice",
    "pixabay": "audio_search",
    "remotion": "compose",
}


def stage_subdir(stage_id: str) -> str:
    """`s02_cut_videos` -> `stage-02-cut-videos`."""
    m = re.match(r"^s(\d+)_(.+)$", stage_id)
    if not m:
        return f"stage-{stage_id.replace('_', '-')}"
    return f"stage-{m.group(1)}-{m.group(2).replace('_', '-')}"


@dataclass
class Item:
    id: str
    prompt: str = ""
    references: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


class StageError(RuntimeError):
    pass


class Pipeline:
    def __init__(
        self,
        cfg: ProjectConfig,
        project_dir: Path,
        run_dir: Path,
        dry_run: bool = False,
        auto_approve: bool = False,
        only: str | None = None,
        from_stage: str | None = None,
    ):
        self.cfg = cfg
        self.project_dir = project_dir
        self.run_dir = run_dir
        self.dry_run = dry_run
        self.auto_approve = auto_approve
        self.only = only
        self.from_stage = from_stage
        self.state: RunState | None = None
        self._adapters: dict[str, Any] = {}

    # -- public --------------------------------------------------------------

    async def run(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.state = RunState.create(
            self.run_dir,
            project_id=self.cfg.project.id,
            config_snapshot=self.cfg.model_dump(mode="json"),
        )

        order = self._topo_order()
        if self.from_stage:
            if self.from_stage not in order:
                raise StageError(f"--from {self.from_stage}: stage not in plan")
            order = order[order.index(self.from_stage) :]
        if self.only:
            if self.only not in order:
                raise StageError(f"--only {self.only}: stage not in plan")
            order = [self.only]

        for sid in order:
            spec = self.cfg.stages[sid]
            if not spec.enabled:
                console.print(f"[dim]· {sid}: disabled, skipping[/dim]")
                self.state.set_stage_status(sid, "skipped")
                continue
            await self._run_stage(sid, spec)

        console.print(f"\n[green]✓ Run complete:[/green] {self.run_dir}")

    # -- stage orchestration -------------------------------------------------

    async def _run_stage(self, stage_id: str, spec: StageSpec) -> None:
        kind = ADAPTER_KIND.get(spec.adapter)
        if kind is None:
            raise StageError(
                f"Stage {stage_id}: adapter '{spec.adapter}' has no kind mapping in ADAPTER_KIND"
            )

        stage_dir = self.run_dir / stage_subdir(stage_id)
        stage_dir.mkdir(parents=True, exist_ok=True)
        console.rule(f"[bold cyan]{stage_id}[/bold cyan]  adapter={spec.adapter}  kind={kind}")
        self.state.set_stage_status(stage_id, "running")

        if kind == "compose":
            await self._run_compose(stage_id, spec, stage_dir)
        else:
            items = list(self._resolve_items(stage_id, spec, kind))
            if not items:
                console.print(f"[yellow]{stage_id}: no items to process[/yellow]")
            for it in items:
                await self._run_item_with_gate(stage_id, spec, kind, stage_dir, it)

        self.state.set_stage_status(stage_id, "generated")

        if kind != "compose" and not self.auto_approve and self.cfg.approval.mode == "gate":
            from creativeforge.ui.approve import approve_stage

            decision = await approve_stage(stage_id, stage_dir, self.run_dir)
            if decision == "quit":
                self.state.set_stage_status(stage_id, "aborted")
                raise StageError(f"User aborted at {stage_id}")
            # Regenerations happen inline inside approve_stage via the regen callback
            # (it calls back into the pipeline). For MVP we just record approval here.

        self.state.set_stage_status(stage_id, "approved")

    async def _run_item_with_gate(
        self,
        stage_id: str,
        spec: StageSpec,
        kind: str,
        stage_dir: Path,
        item: Item,
    ) -> None:
        info = await self._dispatch(stage_id, spec, kind, stage_dir, item)
        self.state.record_item(stage_id, item.id, info)

    # -- adapter dispatch ---------------------------------------------------

    async def _dispatch(
        self,
        stage_id: str,
        spec: StageSpec,
        kind: str,
        stage_dir: Path,
        item: Item,
    ) -> dict[str, Any]:
        console.print(f"  • [bold]{item.id}[/bold] — {item.extra.get('label', item.prompt[:60])}")
        if self.dry_run:
            return {"status": "dry_run", "prompt": item.prompt[:200]}

        prompt = self._apply_override(item)
        started = datetime.now(timezone.utc).isoformat()

        # Lets browser/selectors.dump_debug() write to runs/<id>/debug/ on miss.
        token = CURRENT_RUN_DIR.set(self.run_dir)
        try:
            adapter = self._get_adapter(spec.adapter)
            if kind in ("image", "video"):
                refs = self._resolve_references(item.references)
                req = GenRequest(
                    prompt=prompt,
                    references=refs,
                    aspect_ratio=spec.aspect_ratio or "9:16",
                    model=spec.model,
                    extra={"item_id": item.id, **item.extra},
                )
                result: GenResult = await adapter.generate(req, stage_dir)
                self._write_meta(stage_dir, item.id, result, item, started)
                self.state.record_model(spec.adapter, result.model_used)
                return {"status": "ok", "path": str(result.path), "model": result.model_used}

            if kind == "voice":
                voice = item.extra.get("voice") or spec.voice or "ko-KR-InJoonNeural"
                style = item.extra.get("style")
                result = await adapter.synthesize(
                    text=prompt,
                    voice=voice,
                    out_dir=stage_dir,
                    style=style,
                    item_id=item.id,
                )
                self._write_meta(stage_dir, item.id, result, item, started)
                self.state.record_model(spec.adapter, result.model_used)
                return {"status": "ok", "path": str(result.path), "model": result.model_used}

            if kind == "audio_search":
                kind_q = item.extra.get("kind", "music")
                results = await adapter.search_and_pick(
                    query=prompt,
                    kind=kind_q,
                    duration_s=item.extra.get("duration_s"),
                    out_dir=stage_dir,
                    top_k=item.extra.get("top_k", 3),
                )
                for r in results:
                    self._write_meta(stage_dir, r.path.stem, r, item, started)
                if results:
                    self.state.record_model(spec.adapter, results[0].model_used)
                return {
                    "status": "ok",
                    "paths": [str(r.path) for r in results],
                    "model": results[0].model_used if results else None,
                }

            raise StageError(f"Unsupported adapter kind {kind} at {stage_id}/{item.id}")
        except NotImplementedError as e:
            console.print(f"    [yellow]stub: {e}[/yellow]")
            return {"status": "stub", "error": str(e)}
        except Exception as e:
            console.print(f"    [red]error: {e}[/red]")
            return {"status": "error", "error": str(e)}
        finally:
            CURRENT_RUN_DIR.reset(token)

    async def _run_compose(
        self, stage_id: str, spec: StageSpec, stage_dir: Path
    ) -> None:
        out_name = spec.output_filename or "final.mp4"
        out_path = stage_dir / out_name
        if self.dry_run:
            console.print(f"  [dim]dry_run: would render to {out_path}[/dim]")
            self.state.record_item(stage_id, out_name, {"status": "dry_run"})
            return
        try:
            adapter = self._get_adapter(spec.adapter)
            result_path = await adapter.render(self.project_dir, self.run_dir, out_path)
            self.state.record_item(
                stage_id, out_name, {"status": "ok", "path": str(result_path)}
            )
        except NotImplementedError as e:
            console.print(f"  [yellow]stub: {e}[/yellow]")
            self.state.record_item(stage_id, out_name, {"status": "stub", "error": str(e)})

    # -- item resolution -----------------------------------------------------

    def _resolve_items(
        self, stage_id: str, spec: StageSpec, kind: str
    ) -> Iterable[Item]:
        if kind in ("image", "video"):
            if not spec.prompts_file:
                raise StageError(f"{stage_id}: image/video stage needs prompts_file")
            data = self._load_yaml(self.project_dir / spec.prompts_file)
            items = data.get("items") or {}
            for item_id, body in items.items():
                yield Item(
                    id=item_id,
                    prompt=body.get("prompt", ""),
                    references=body.get("references") or [],
                    extra={"label": body.get("label") or body.get("title", "")},
                )
            return

        if kind == "voice":
            sb = self._load_yaml(self.project_dir / self.cfg.storyboard_file)
            for cut in sb.get("cuts", []):
                d = cut.get("dialogue")
                if not d or not d.get("text"):
                    continue
                yield Item(
                    id=cut["id"],
                    prompt=d["text"],
                    extra={
                        "label": cut.get("label", ""),
                        "voice": d.get("voice"),
                        "style": d.get("style"),
                    },
                )
            return

        if kind == "audio_search":
            if not spec.keywords_file:
                raise StageError(f"{stage_id}: audio_search stage needs keywords_file")
            data = self._load_yaml(self.project_dir / spec.keywords_file)
            for i, q in enumerate(data.get("music_queries") or []):
                yield Item(
                    id=f"music-{i:02d}",
                    prompt=q,
                    extra={"label": q[:60], "kind": "music"},
                )
            for i, q in enumerate(data.get("sfx_queries") or []):
                yield Item(
                    id=f"sfx-{i:02d}",
                    prompt=q,
                    extra={"label": q[:60], "kind": "sfx"},
                )
            return

        raise StageError(f"_resolve_items: unsupported kind {kind}")

    # -- references / overrides / meta --------------------------------------

    def _resolve_references(self, refs: list[str]) -> list[Path]:
        """Best-effort: 'Sheet 3 (Suyang)' -> stage-00 file starting with 'sheet3'.

        Misses are logged but don't abort — the adapter may still produce a
        useful result, and the user can fix labels in DECISIONS.md follow-ups.
        """
        out: list[Path] = []
        sheets_dir = self.run_dir / stage_subdir("s00_character_sheets")
        cut_imgs_dir = self.run_dir / stage_subdir("s01_cut_images")
        for ref in refs:
            m = re.search(r"sheet\s*(\d+)", ref, re.I)
            if m:
                num = m.group(1)
                hits = list(sheets_dir.glob(f"sheet{num}*.png")) + list(
                    sheets_dir.glob(f"sheet{num}*.jpg")
                )
                if hits:
                    out.append(hits[0])
                    continue
            m = re.search(r"cut\s*0*(\d+)", ref, re.I)
            if m:
                hits = list(cut_imgs_dir.glob(f"cut{int(m.group(1)):02d}*.png")) + list(
                    cut_imgs_dir.glob(f"cut{int(m.group(1)):02d}*.jpg")
                )
                if hits:
                    out.append(hits[0])
                    continue
            console.print(f"    [yellow]reference unresolved: {ref!r}[/yellow]")
        return out

    def _apply_override(self, item: Item) -> str:
        override_dir = self.run_dir / "prompt-overrides"
        path = override_dir / f"{item.id}.yaml"
        if path.exists():
            data = self._load_yaml(path)
            if isinstance(data, dict) and data.get("prompt"):
                console.print(f"    [dim]using prompt override from {path.name}[/dim]")
                return data["prompt"]
        return item.prompt

    def _write_meta(
        self,
        stage_dir: Path,
        item_id: str,
        result: GenResult,
        item: Item,
        started: str,
    ) -> None:
        meta = {
            "item_id": item_id,
            "prompt": item.prompt,
            "references": item.references,
            "started_at": started,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "model_used": result.model_used,
            "source_url": result.source_url,
            "raw_meta": result.raw_meta,
            "path": str(result.path),
        }
        (stage_dir / f"{item_id}.meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False)
        )

    # -- helpers ------------------------------------------------------------

    def _get_adapter(self, name: str):
        if name not in self._adapters:
            cls = get_adapter(name)
            # Flow adapters need browser config + project dir for .auth/ paths.
            if name in ("google_flow_imagen", "google_flow_veo"):
                self._adapters[name] = cls(
                    browser_cfg=self.cfg.browser,
                    project_dir=self.project_dir,
                )
            else:
                self._adapters[name] = cls()
        return self._adapters[name]

    def _load_yaml(self, path: Path) -> dict:
        with path.open() as f:
            return yaml.load(f) or {}

    def _topo_order(self) -> list[str]:
        stages = self.cfg.stages
        order: list[str] = []
        visited: set[str] = set()
        visiting: set[str] = set()

        def visit(sid: str) -> None:
            if sid in visited:
                return
            if sid in visiting:
                raise StageError(f"Cycle detected involving {sid}")
            visiting.add(sid)
            for dep in stages[sid].depends_on:
                if dep not in stages:
                    raise StageError(f"{sid} depends_on unknown stage {dep}")
                visit(dep)
            visiting.discard(sid)
            visited.add(sid)
            order.append(sid)

        for sid in stages:
            visit(sid)
        return order


async def run_pipeline(
    cfg: ProjectConfig,
    project_dir: Path,
    run_dir: Path,
    *,
    dry_run: bool = False,
    auto_approve: bool = False,
    only: str | None = None,
    from_stage: str | None = None,
) -> None:
    p = Pipeline(
        cfg=cfg,
        project_dir=project_dir,
        run_dir=run_dir,
        dry_run=dry_run,
        auto_approve=auto_approve,
        only=only,
        from_stage=from_stage,
    )
    await p.run()
