"""Interactive approval gate between stages.

Keys per item:
    a — approve
    r — mark for regenerate (writes a marker in prompt-overrides/ so caller can re-run)
    e — open $EDITOR on the prompt override; auto-marks for regenerate
    i — inspect / open artifact(s) in OS default viewer (xdg-open / open / start)
    v — pick which generated variant to keep (when more than one was rendered)
    s — skip this item
    q — abort the run

The gate returns ``(decision, regen_ids)`` — the decision is one of `approved`,
`regen`, `skip`, `quit`, and `regen_ids` holds the items marked `[r]`/`[e]`. The
pipeline (`Pipeline._run_stage`) re-runs exactly those items and re-opens the
gate until the stage is approved/skipped/quit.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

Decision = Literal["approved", "regen", "skip", "quit"]
ApproveResult = tuple[Decision, list[str]]  # (decision, regen_item_ids)
console = Console()

VALID_KEYS = {"a", "r", "e", "i", "v", "s", "q"}


def select_variant(
    run_dir: Path, stage_dir: Path, stage_id: str, item_id: str, index: int
) -> Path:
    """Promote variant `index` to the canonical artifact for `item_id`.

    Copies the chosen variant over `stage_dir/<item_id><ext>` and rewrites that
    item's `path` in `state.json`. Returns the canonical path. Raises IndexError
    if the item has no variant at `index`.
    """
    items = _load_stage_items(run_dir, stage_id)
    info = items.get(item_id) or {}
    variants = info.get("paths") or ([info["path"]] if info.get("path") else [])
    if not 0 <= index < len(variants):
        raise IndexError(f"{item_id}: no variant {index} (have {len(variants)})")

    chosen = Path(variants[index])
    canonical = stage_dir / f"{item_id}{chosen.suffix}"
    if chosen.resolve() != canonical.resolve():
        shutil.copyfile(chosen, canonical)

    state_path = run_dir / "state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))
    data["stages"][stage_id]["items"][item_id]["path"] = str(canonical)
    state_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return canonical


def _open_in_os(path: Path) -> None:
    if not path.exists():
        console.print(f"  [red]not found: {path}[/red]")
        return
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        elif sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            opener = shutil.which("xdg-open") or "xdg-open"
            subprocess.Popen([opener, str(path)])
    except Exception as e:
        console.print(f"  [red]open failed: {e}[/red]")


def _edit_override(run_dir: Path, item_id: str, current_prompt: str) -> Path:
    override_dir = run_dir / "prompt-overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    path = override_dir / f"{item_id}.yaml"
    if not path.exists():
        path.write_text(
            "# Override the prompt for this item. The pipeline reads this on regenerate.\n"
            "prompt: |\n  "
            + current_prompt.replace("\n", "\n  ")
            + "\n",
            encoding="utf-8",
        )
    editor = os.environ.get("EDITOR") or ("notepad" if sys.platform.startswith("win") else "nano")
    subprocess.call([editor, str(path)])
    return path


def _load_stage_items(run_dir: Path, stage_id: str) -> dict[str, dict]:
    state_path = run_dir / "state.json"
    if not state_path.exists():
        return {}
    data = json.loads(state_path.read_text(encoding="utf-8"))
    return ((data.get("stages") or {}).get(stage_id) or {}).get("items") or {}


def _render_table(stage_id: str, items: dict[str, dict], stage_dir: Path) -> None:
    table = Table(title=f"Stage {stage_id} — review")
    table.add_column("item")
    table.add_column("status")
    table.add_column("artifact")
    for item_id, info in items.items():
        artifact = info.get("path") or (
            ", ".join(Path(p).name for p in info.get("paths", [])) or "-"
        )
        table.add_row(item_id, info.get("status", "?"), Path(artifact).name if isinstance(artifact, str) and artifact != "-" else str(artifact))
    console.print(table)


async def approve_stage(stage_id: str, stage_dir: Path, run_dir: Path) -> "ApproveResult":
    """Walk through all items in a stage, prompting per item.

    Returns ``(decision, regen_ids)`` where:
      - decision ``"quit"``     — user pressed ``q``; regen_ids is empty
      - decision ``"regen"``    — items in regen_ids need to be re-run
      - decision ``"skip"``     — all items skipped; regen_ids is empty
      - decision ``"approved"`` — all items approved; regen_ids is empty
    """
    items = _load_stage_items(run_dir, stage_id)
    if not items:
        console.print(f"[dim]{stage_id}: nothing to approve[/dim]")
        return "approved", []

    _render_table(stage_id, items, stage_dir)
    console.print(
        "[dim]keys: [a]pprove  [r]egenerate  [e]dit prompt  [i]nspect  [s]kip  [q]uit[/dim]"
    )

    regen_ids: list[str] = []
    all_skipped = True

    for item_id, info in items.items():
        variant_paths = [Path(p) for p in (info.get("paths") or [])]
        if not variant_paths and info.get("path"):
            variant_paths = [Path(info["path"])]
        artifact_path = Path(info["path"]) if info.get("path") else (
            variant_paths[0] if variant_paths else None
        )
        if len(variant_paths) > 1:
            console.print(f"    [dim]{len(variant_paths)} variants — press [v] to pick the best[/dim]")

        while True:
            choice = Prompt.ask(
                f"  {item_id}",
                choices=sorted(VALID_KEYS),
                default="a",
                show_choices=False,
            ).strip().lower()
            if choice not in VALID_KEYS:
                console.print("    [red]invalid key[/red]")
                continue
            if choice == "i":
                to_open = variant_paths or ([artifact_path] if artifact_path else [])
                if to_open:
                    for p in to_open:
                        _open_in_os(p)
                else:
                    console.print("    [yellow]no artifact to inspect[/yellow]")
                continue
            if choice == "v":
                if len(variant_paths) <= 1:
                    console.print("    [yellow]only one variant — nothing to pick[/yellow]")
                    continue
                raw = Prompt.ask(
                    f"    variant index [0-{len(variant_paths) - 1}]", default="0"
                ).strip()
                if not raw.isdigit():
                    console.print("    [red]not a number[/red]")
                    continue
                try:
                    chosen = select_variant(run_dir, stage_dir, stage_id, item_id, int(raw))
                except IndexError as e:
                    console.print(f"    [red]{e}[/red]")
                    continue
                artifact_path = chosen
                console.print(f"    [green]kept variant {raw} → {chosen.name}[/green]")
                continue
            if choice == "e":
                prompt_text = ""
                meta_path = stage_dir / f"{item_id}.meta.json"
                if meta_path.exists():
                    try:
                        prompt_text = json.loads(meta_path.read_text(encoding="utf-8")).get("prompt", "")
                    except Exception:
                        pass
                _edit_override(run_dir, item_id, prompt_text)
                regen_ids.append(item_id)
                all_skipped = False
                console.print("    [yellow]marked for regenerate[/yellow]")
                break
            if choice == "r":
                regen_ids.append(item_id)
                all_skipped = False
                console.print("    [yellow]marked for regenerate[/yellow]")
                break
            if choice == "a":
                all_skipped = False
                break
            if choice == "s":
                break
            if choice == "q":
                return "quit", []

    if regen_ids:
        return "regen", regen_ids
    if all_skipped:
        return "skip", []
    return "approved", []
