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


class TestCredits:
    def test_cost_per_video_flat_models(self):
        from creativeforge.credits import cost_per_video
        assert cost_per_video("veo-3.1-high-quality") == 100
        assert cost_per_video("veo-3.1-fast") == 20
        assert cost_per_video("veo-3.1-lite") == 10

    def test_cost_per_video_unknown_is_free(self):
        from creativeforge.credits import cost_per_video
        assert cost_per_video("imagen-4-ultra") == 0
        assert cost_per_video(None) == 0

    def test_omni_flash_duration_buckets(self):
        from creativeforge.credits import cost_per_video
        assert cost_per_video("omni-flash", duration_s=4) == 15
        assert cost_per_video("omni-flash", duration_s=6) == 20
        assert cost_per_video("omni-flash", duration_s=8) == 25
        assert cost_per_video("omni-flash", duration_s=10) == 30
        # 5s rounds up to the 6s bucket; 12s clamps to the largest bucket
        assert cost_per_video("omni-flash", duration_s=5) == 20
        assert cost_per_video("omni-flash", duration_s=12) == 30

    def test_estimate_item_multiplies_variants(self):
        from creativeforge.credits import estimate_item
        assert estimate_item("veo-3.1-high-quality", variants=4) == 400
        assert estimate_item("veo-3.1-fast", variants=4) == 80

    def test_estimate_plan_splits_by_source(self):
        from creativeforge.credits import estimate_plan
        cuts = [
            {"id": "a", "model": "veo-3.1-high-quality", "variants": 1, "source": "flow"},
            {"id": "b", "model": "veo-3.1-fast", "variants": 1, "source": "flow"},
            {"id": "c", "model": "omni-flash", "duration_s": 4, "variants": 1, "source": "gemini"},
        ]
        plan = estimate_plan(cuts, default_model="veo-3.1-fast")
        assert plan["totals"]["flow"] == 120
        assert plan["totals"]["gemini"] == 15
        assert plan["grand_total"] == 135

    def test_project_plan_within_budget(self):
        from creativeforge.pipeline import plan_video_credits
        cfg = ProjectConfig.load(PROJECT_DIR)
        plan = plan_video_credits(PROJECT_DIR, cfg)
        assert plan is not None
        # Draft-first: all 9 cuts start on veo-3.1-fast (9 x 20 = 180).
        assert plan["totals"]["flow"] == 180
        assert plan["totals"]["flow"] <= cfg.credits.monthly_budget


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


class TestVariantSelection:
    def test_select_variant_promotes_chosen_index(self, tmp_path):
        import json
        from creativeforge.ui.approve import select_variant

        run_dir = tmp_path
        stage_id = "s01_cut_images"
        stage_dir = run_dir / "stage-01-cut-images"
        stage_dir.mkdir(parents=True)
        variants = []
        for i in range(4):
            p = stage_dir / f"cut01-v{i}.png"
            p.write_text(f"variant-{i}")
            variants.append(str(p))
        # canonical currently = v0
        canonical_seed = stage_dir / "cut01.png"
        canonical_seed.write_text("variant-0")

        state = {
            "stages": {
                stage_id: {
                    "status": "generated",
                    "items": {
                        "cut01": {"status": "ok", "path": str(canonical_seed), "paths": variants}
                    },
                }
            }
        }
        (run_dir / "state.json").write_text(json.dumps(state))

        result = select_variant(run_dir, stage_dir, stage_id, "cut01", 2)
        assert result.name == "cut01.png"
        assert result.read_text() == "variant-2"
        # state path now points at the canonical artifact
        reloaded = json.loads((run_dir / "state.json").read_text())
        assert reloaded["stages"][stage_id]["items"]["cut01"]["path"] == str(result)

    def test_select_variant_out_of_range_raises(self, tmp_path):
        import json
        from creativeforge.ui.approve import select_variant

        stage_dir = tmp_path / "stage-01-cut-images"
        stage_dir.mkdir(parents=True)
        v0 = stage_dir / "cut01-v0.png"
        v0.write_text("v0")
        state = {
            "stages": {
                "s01_cut_images": {
                    "items": {"cut01": {"path": str(v0), "paths": [str(v0)]}}
                }
            }
        }
        (tmp_path / "state.json").write_text(json.dumps(state))
        with pytest.raises(IndexError):
            select_variant(tmp_path, stage_dir, "s01_cut_images", "cut01", 3)

    def test_genresult_without_variants_exposes_single_path(self):
        from creativeforge.adapters.base import GenResult

        r = GenResult(path=Path("/tmp/x.png"), model_used="imagen-4-ultra")
        assert r.variant_paths == []
        # pipeline treats empty variant_paths as [path]
        assert (r.variant_paths or [r.path]) == [Path("/tmp/x.png")]
