# CLAUDE.md — creativeforge operating rules

> Auto-loaded at session start. This file describes the project **as it actually
> is in the code today**, including what is *not* built yet. If you add or remove
> a capability, update this file in the same commit so the next session isn't
> misled. Deeper history + the Windows/Phase B runbook live in `HANDOFF.md`.

## What this is

`creativeforge` is a multi-project AI video pipeline. Reusable core
(`creativeforge/`) + per-project data (`projects/<name>/`). First resident
project: `projects/musinsa-king-choice/` — 무신사 무진장 광고제 2026 출품작
"왕의 선택" (30s, 9:16 vertical).

## Ground truth: what exists vs. what does NOT (read before planning)

**Implemented and verified runnable (cloud-side):**
- CLI: `creativeforge list | doctor | run | resume` (`creativeforge/cli.py`).
  `run` supports `--dry-run`, `--auto-approve`, `--only <stage>`, `--from <stage>`.
- Pipeline orchestration with topological stage order + per-item `state.json`
  persistence (`pipeline.py`, `state.py`).
- Approval gate `[a/r/e/i/s/q]` with a **wired regenerate loop** — `[r]`/`[e]`
  re-runs exactly the flagged items, then re-opens the gate (`ui/approve.py` +
  `Pipeline._run_stage`).
- `resume <run_id>` — reloads `state.json` and restarts from the first
  non-approved/skipped stage in the same run dir.
- Adapters: `edge_tts` (voice), `pixabay` (music/SFX search), `remotion`
  (compose). HTTP/subprocess — no browser needed.
- Browser scaffolding: `browser/session.py` (persistent context),
  `browser/selectors.py` (`first_visible` fallback chains + debug dump on miss),
  and **first-guess** Playwright flows `browser/flow_imagen.py` / `flow_veo.py`.

**Does NOT exist yet (do not assume these; build or flag before relying on them):**
- ❌ **No credits/budget system.** Nothing tracks or enforces a monthly credit
  budget. The only credit awareness is *detection*: `flow_veo._wait_for_render`
  raises `RuntimeError("credit_exhausted: …")` if Flow shows a quota message.
  "Draft-first" (below) is therefore a **manual discipline**, not enforced code.
- ❌ **No variant picker.** `flow_imagen` downloads variant index 0
  (`_download_first_variant`). Choosing the best of N is manual today.
- ❌ **No Voicebox / Kokoro / Chatterbox / Clova / ElevenLabs adapter.** The only
  voice adapter is `edge_tts`. `project.yaml` once referenced
  `fallback_adapter: clova` — that's commented out because no such adapter is
  registered. Swapping TTS means *writing a new adapter* (recipe below), not a
  config flip.
- ❌ **No process-doc / AI-capture → PDF** automation. Listed as v2 in `HANDOFF.md`.
- ❌ **No automated tests** (`tests/` does not exist). Verify via the dry-run.
- ⚠️ **Flow selectors are first-guess and will mostly miss** until iterated. That
  iteration ("Phase B") is the main open task and **must run on Windows** with a
  real, headed browser + interactive Google login — not in a headless cloud
  container. See `HANDOFF.md`.

## Operating rules

### Draft-first credit discipline (MANUAL)
Veo HQ burns ~3x credits (`flow_veo._ensure_high_quality`). Until a budget system
exists: iterate prompts/selectors against Imagen (cheap) and Veo drafts, approve
the still frame via the gate, and only run final HQ Veo on approved cuts. Treat
`credit_exhausted` as a hard stop and tell the user.

### Variant picking (MANUAL)
The Flow adapter grabs the first variant. To pick a different one, use the gate:
`[i]` to inspect, `[e]` to edit the prompt, `[r]` to regenerate. If you automate
selection later, do it in `flow_imagen._download_first_variant` and update this file.

### Voice strategy
Default `edge_tts` (`ko-KR-InJoonNeural`, sajeok styles in
`EdgeTtsAdapter.STYLE_SSML`). The open judgment call: if edge-tts can't carry the
cut05 "무진장!" delivery, swap TTS — but that requires a **new adapter**, not a
config change (see recipe). Listen before deciding.

## Extend recipes

**Add an adapter:** create `creativeforge/adapters/<kind>/<name>.py`, decorate the
class with `@register("<name>")`, implement the matching Protocol in
`adapters/base.py` (`generate` / `synthesize` / `search_and_pick` / `render`),
import it from `adapters/__init__.py` so the registry populates, then add a
`"<name>": "<kind>"` entry to `ADAPTER_KIND` in `pipeline.py`. Verify with
`creativeforge doctor`.

**Add a project:** drop `projects/<name>/` with `project.yaml` (+ prompts,
storyboard, branding, remotion). `creativeforge list` should show it; validate
with `creativeforge run <name> --dry-run --auto-approve`.

## Verify quickly
```bash
pip install -e .
creativeforge doctor                                            # 5 adapters
creativeforge run musinsa-king-choice --dry-run --auto-approve  # full plan, no spend
```
Live Flow (Imagen/Veo) work needs Windows + a logged-in browser — see `HANDOFF.md`.
