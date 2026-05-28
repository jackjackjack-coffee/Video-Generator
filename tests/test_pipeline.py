"""Pipeline unit tests — cloud-runnable, no browser required."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from creativeforge.config import ProjectConfig
from creativeforge.pipeline import Pipeline

PROJECT_DIR = Path("projects/musinsa-king-choice")


def _make_pipeline(**kwargs) -> Pipeline:
    cfg = ProjectConfig.load(PROJECT_DIR)
    return Pipeline(
        cfg=cfg,
        project_dir=PROJECT_DIR,
        run_dir=Path("/tmp/cf-test-run"),
        **kwargs,
    )


class TestAudioQueryResolution:
    def test_only_real_queries_yielded(self):
        p = _make_pipeline()
        spec = p.cfg.stages["s04_audio"]
        items = list(p._resolve_items("s04_audio", spec, "audio_search"))
        prompts = [it.prompt for it in items]
        # Real Pixabay queries should be present
        assert "japanese sad traditional" in prompts
        assert "trap beat short" in prompts
        assert "sword clash metal" in prompts
        # Human notes must NOT appear as queries
        for prompt in prompts:
            assert "BPM" not in prompt
            assert "보컬" not in prompt
            assert "느림" not in prompt

    def test_item_ids_are_group_prefixed(self):
        p = _make_pipeline()
        spec = p.cfg.stages["s04_audio"]
        items = list(p._resolve_items("s04_audio", spec, "audio_search"))
        ids = [it.id for it in items]
        assert any(i.startswith("bgm-traditional") for i in ids)
        assert any(i.startswith("bgm-bright") for i in ids)
        assert any(i.startswith("sfx") for i in ids)

    def test_sfx_kind_is_sfx(self):
        p = _make_pipeline()
        spec = p.cfg.stages["s04_audio"]
        items = list(p._resolve_items("s04_audio", spec, "audio_search"))
        sfx_items = [it for it in items if it.id.startswith("sfx")]
        assert sfx_items, "no sfx items found"
        for it in sfx_items:
            assert it.extra["kind"] == "sfx"


class TestVisualStyleInjection:
    def test_drama_suffix_on_cuts_01_to_05(self):
        p = _make_pipeline()
        spec = p.cfg.stages["s01_cut_images"]
        items = {it.id: it for it in p._resolve_items("s01_cut_images", spec, "image")}
        for cid in ("cut01", "cut02", "cut03", "cut04", "cut05"):
            assert "Color grade: dark cinematic" in items[cid].prompt, cid

    def test_fashion_suffix_on_cuts_06_to_09(self):
        p = _make_pipeline()
        spec = p.cfg.stages["s01_cut_images"]
        items = {it.id: it for it in p._resolve_items("s01_cut_images", spec, "image")}
        for cid in ("cut06", "cut07", "cut08", "cut09"):
            assert "Color grade: bright editorial" in items[cid].prompt, cid

    def test_no_cross_contamination(self):
        p = _make_pipeline()
        spec = p.cfg.stages["s01_cut_images"]
        items = {it.id: it for it in p._resolve_items("s01_cut_images", spec, "image")}
        for cid in ("cut01", "cut02", "cut03", "cut04", "cut05"):
            assert "Color grade: bright editorial" not in items[cid].prompt, cid
        for cid in ("cut06", "cut07", "cut08", "cut09"):
            assert "Color grade: dark cinematic" not in items[cid].prompt, cid

    def test_no_double_suffix(self):
        p = _make_pipeline()
        spec = p.cfg.stages["s01_cut_images"]
        items = list(p._resolve_items("s01_cut_images", spec, "image"))
        for it in items:
            assert it.prompt.count("Color grade:") <= 1, it.id


class TestReferenceResolution:
    def test_slug_refs_resolve_when_files_exist(self, tmp_path):
        p = _make_pipeline()
        p.run_dir = tmp_path
        sheets_dir = tmp_path / "stage-00-character-sheets"
        sheets_dir.mkdir(parents=True)
        (sheets_dir / "sheet1-danjong-royal.png").touch()
        (sheets_dir / "sheet3-suyang.png").touch()
        refs = p._resolve_references(["sheet1-danjong-royal", "sheet3-suyang"])
        assert len(refs) == 2
        assert refs[0].name == "sheet1-danjong-royal.png"
        assert refs[1].name == "sheet3-suyang.png"

    def test_legacy_refs_still_resolve(self, tmp_path):
        p = _make_pipeline()
        p.run_dir = tmp_path
        sheets_dir = tmp_path / "stage-00-character-sheets"
        sheets_dir.mkdir(parents=True)
        (sheets_dir / "sheet3-suyang.png").touch()
        refs = p._resolve_references(["Sheet 3 (Suyang)"])
        assert len(refs) == 1

    def test_unresolved_ref_logs_and_skips(self, tmp_path, capsys):
        p = _make_pipeline()
        p.run_dir = tmp_path
        (tmp_path / "stage-00-character-sheets").mkdir(parents=True)
        refs = p._resolve_references(["nonexistent-ref"])
        assert refs == []


class TestRegenLoop:
    def test_regen_loop_reruns_flagged_items(self):
        """When approve_stage returns ('regen', ['cut03']), only cut03 is re-dispatched."""
        p = _make_pipeline()
        p.run_dir = Path("/tmp/cf-regen-test")
        p.run_dir.mkdir(parents=True, exist_ok=True)
        from creativeforge.state import RunState
        p.state = RunState.create(p.run_dir, project_id="musinsa-king-choice", config_snapshot={})

        dispatch_calls: list[str] = []

        async def fake_dispatch(stage_id, spec, kind, stage_dir, item):
            dispatch_calls.append(item.id)
            return {"status": "ok", "path": "/tmp/fake.png"}

        approve_results = [
            ("regen", ["cut03"]),
            ("approved", []),
        ]
        approve_iter = iter(approve_results)

        async def fake_approve(stage_id, stage_dir, run_dir):
            return next(approve_iter)

        spec = p.cfg.stages["s01_cut_images"]
        stage_dir = p.run_dir / "stage-01-cut-images"
        stage_dir.mkdir(parents=True, exist_ok=True)

        with (
            patch.object(p, "_dispatch", side_effect=fake_dispatch),
            patch("creativeforge.ui.approve.approve_stage", side_effect=fake_approve),
        ):
            asyncio.run(p._run_stage("s01_cut_images", spec))

        # Initial pass: 9 cuts; regen pass: only cut03
        assert dispatch_calls.count("cut03") == 2
        for cid in ("cut01", "cut02", "cut04", "cut05", "cut06", "cut07", "cut08", "cut09"):
            assert dispatch_calls.count(cid) == 1
