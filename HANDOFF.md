# HANDOFF — creativeforge initial scaffold

> Picked up by the next session. Read this first.

## What this is

`creativeforge` is a multi-project AI video production pipeline extracted from the standalone `Musinsa-ad-festival` repo. The first resident project is `projects/musinsa-king-choice/` — the 무신사 무진장 광고제 2026 출품작 "왕의 선택" (30s, 9:16).

Design and rationale: see the approved plan referenced in the commit body, summarized in `README.md`.

## What was done in the scaffold session (2026-05-26)

- Repo structure + Python package skeleton (`pyproject.toml`, `creativeforge/` package, `projects/`, `runs/`, `scripts/`, `tests/`).
- Core abstractions: `creativeforge/config.py` (ProjectConfig), `creativeforge/state.py` (RunState), `creativeforge/stages/base.py` (Stage), `creativeforge/adapters/base.py` (Protocols + registry).
- CLI skeleton: `creativeforge/cli.py` — `list`, `doctor`, `run`, `resume`. `list`, `doctor`, and `run` (incl. `--dry-run`, `--auto-approve`, `--only`, `--from`) work end-to-end. `resume` still TODO.
- Adapters **implemented**:
  - `audio/pixabay.py` — Pixabay music/SFX search + download (HTTP, needs `PIXABAY_API_KEY`).
  - `voice/edge_tts.py` — Microsoft Edge TTS with style-based pitch/rate (`royal`, `stern`, `tearful`, `comic`).
  - `compose/remotion.py` — generates `remotion/src/generated/manifest.ts` from `storyboard.yaml`, symlinks artifacts into `remotion/public/`, runs `npx remotion render`.
- Adapters **stubbed** (raise NotImplementedError; module docstring has implementation checklist):
  - `image/google_flow_imagen.py`
  - `video/google_flow_veo.py`
- Browser session helper: `creativeforge/browser/session.py` (persistent context, storage_state fallback).
- Migration script: `scripts/import_musinsa.py` — produced `projects/musinsa-king-choice/` end-to-end.
- Migrated project contents:
  - `project.yaml` — adapter/model declarations.
  - `prompts/00..04.yaml` — parsed from original md (character sheets, cut images, cut videos, audio keywords).
  - `storyboard.yaml` — parsed from `src/constants.ts`. Dialogue auto-tagged with speaker/style (some are heuristic guesses — see "Open issues").
  - `branding/` — copied 5 KV/logo assets.
  - `references/` — empty (existing character sheets weren't in the source repo's `public/references/`; user has them locally).
  - `remotion/` — copied `src/*.tsx`, `package.json`, `tsconfig.json`. `KingsChoice.tsx` patched to import `./generated/manifest` instead of `./constants`.
  - `CONTEXT.md` + `DECISIONS.md` — initial drafts.

## Completed in session 2026-05-26-b

- **`creativeforge/pipeline.py`** — stage orchestration in topological order, adapter dispatch by kind (image/video/voice/audio_search/compose), per-item artifact + `.meta.json` write, `state.json` persisted after every item, `--only` / `--from` flags supported. `dry_run` skips adapter construction (so missing API keys don't block planning).
- **`creativeforge/ui/approve.py`** — interactive per-item gate with rich table, `[a/r/e/i/s/q]` keys, `xdg-open`/`open`/`os.startfile` preview, `$EDITOR` opens `runs/<id>/prompt-overrides/<item>.yaml`. Returns aggregate decision (`approved` / `regen` / `skip` / `quit`).
- **Edge-TTS pitch bug fix** — pitch values switched from `%` (invalid) to `Hz` (required by edge-tts). Caught while smoke-testing real voice generation.

## Completed in session 2026-05-27 (Phase A scaffolding for Flow adapters)

- **`creativeforge/browser/selectors.py`** — `first_visible(page, candidates, label)` walks a fallback list of locator factories and returns the first visible one; raises `SelectorMiss` with a debug dump (HTML + screenshot) on full miss. Also exposes `LoginRequired` and a `CURRENT_RUN_DIR` ContextVar so dumps land under `runs/<id>/debug/`.
- **`creativeforge/browser/flow_imagen.py`** + **`flow_veo.py`** — full Playwright flows (navigate → model pick → aspect ratio → reference upload → prompt → submit → wait → download). Selectors are first-guess fallback chains; expect heavy iteration in the paired session.
- **`creativeforge/adapters/image/google_flow_imagen.py`** + **`adapters/video/google_flow_veo.py`** — stubs replaced with Protocol-thin wrappers that open `headed_context` and hand the Page to the helpers. Accept `(browser_cfg, project_dir)`.
- **`creativeforge/pipeline.py`** — `_get_adapter` injects `browser_cfg` + `project_dir` for the Flow adapters only; `_dispatch` sets `CURRENT_RUN_DIR` around the call.
- **`scripts/login_google_flow.py`** — one-time login bootstrap (opens Flow, waits for manual sign-in, snapshots `.auth/chrome-profile/` + `.auth/google.json`).
- Dry-run + import sanity verified in the cloud sandbox; the live UI work must happen on the user's Windows machine.

## What's NOT done — picked-up tasks

### High priority

1. **Phase B: paired selector iteration** (Windows, local Claude Code session).
   - Bootstrap: `python scripts/login_google_flow.py`.
   - **Confirm the image-tool UI flow first:** `python scripts/probe_image_tool.py`
     (read-only — navigates + dumps element maps to `runs/_probe/<ts>/`, never submits).
   - Test target: `creativeforge run musinsa-king-choice --only s00_character_sheets --auto-approve`.
   - First-guess selectors are committed but will mostly miss. Each miss dumps `runs/<id>/debug/<ts>-<label>.{html,png}`. Iterate by prepending new candidate lambdas in `creativeforge/browser/flow_imagen.py` and `flow_veo.py`. Keep older candidates at the bottom — they self-heal across Flow A/B tests.
   - Tools: `playwright codegen https://labs.google/fx/tools/flow --load-storage .auth/google.json`, `set PWDEBUG=1`.

   **Image-mode UI discovered 2026-05-31 (UNVERIFIED — pre-seeded as TOP candidates in `flow_imagen.py`):**
   `새 프로젝트` → close agent panel (`닫기`) → click the **`에이전트` pill** (this switches
   the prompt bar into DIRECT image generation; model defaults to Imagen 4) → a combined
   config button reading **`Imagen 4 crop_16_9 x2`** exposes model (Imagen 4 / Nano Banana),
   aspect (`crop_16_9` / `crop_9_16`), count (`x2`) → `만들기` / arrow_forward submits →
   tiles land in **`모든 미디어`**. The radix id (e.g. `radix-:r3s:`) is non-deterministic —
   match on text, never the id. **9:16 maps to the `crop_9_16` token** (the old code passed
   the literal `9:16` and missed; `_ASPECT_TOKENS` in `flow_imagen.py` now maps it).

2. **Regenerate loop wiring**. `ui/approve.py` reports `regen` but `pipeline._run_stage` only logs the decision. Wire `regen` → re-run flagged items in place, then re-prompt. Look for the `# Regenerations happen inline ...` comment in `pipeline.py:_run_stage`.

3. **`resume <run_id>`** — load `state.json`, find the first non-`approved` stage, restart `Pipeline` from there. The infrastructure (`RunState.load`, `--from`) exists; needs a thin wrapper that derives the start stage automatically.

### Medium priority

4. Hand-edit `projects/musinsa-king-choice/CONTEXT.md` and `DECISIONS.md` — they're auto-generated drafts. Verify the "current progress" section against reality.
5. Review `projects/musinsa-king-choice/storyboard.yaml` — speaker tags were manually corrected for cut04 (danjong) and cut09 (danjong), plus dialogue text fixed to "숙부, 어찌하여…". Other cuts looked fine on a quick check but a full pass against the original PLAN.md cuts table is still worth doing.
6. Normalize reference IDs in `prompts/01-cut-images.yaml` and `prompts/02-cut-videos.yaml`. Currently they read `Sheet 3 (Suyang)`. `pipeline._resolve_references()` does a best-effort `sheet(\d+)` regex match, but a clean slug like `sheet3-prince-suyang-수양대군` would be more robust.
7. Sheet IDs in `prompts/00-character-sheets.yaml` carry Korean in the slug (`sheet1-king-danjong-조선-왕복-버전`). Decide: normalize to `sheet1-danjong-royal`, `sheet2-danjong-modern`, etc. and update reference fields throughout.
8. `prompts/04-audio-keywords.yaml` mixes actual queries (`"japanese sad traditional"`) with style notes (`60~80 BPM (느림)`). The pixabay adapter currently treats every line as a query — prune to real queries or add a separate `queries` block.

### Low priority / v2

9. `creativeforge doctor` should check adapter health (PIXABAY_API_KEY present, edge-tts reachable, npm/remotion present).
10. Approval gate web UI (FastAPI + simple HTML) — easier preview than `xdg-open`.
11. Parallel item generation within a stage.
12. AI-process auto-capture → PDF for festival submission.

## How to verify what works right now

```bash
cd Video-Generator
pip install -e .
creativeforge doctor                                       # lists 5 registered adapters
creativeforge list                                         # shows musinsa-king-choice
creativeforge run musinsa-king-choice --dry-run --auto-approve   # full plan, no adapter calls
creativeforge run musinsa-king-choice --only s03_voice --auto-approve   # real edge-tts call
creativeforge run musinsa-king-choice --from s03_voice     # resume-style start
```

To test the Pixabay adapter standalone:

```bash
export PIXABAY_API_KEY=...
python -c "
import asyncio
from pathlib import Path
from creativeforge.adapters.audio.pixabay import PixabayAdapter
out = Path('/tmp/cf-test'); out.mkdir(exist_ok=True)
r = asyncio.run(PixabayAdapter().search_and_pick('joseon korean', 'music', None, out, top_k=3))
for hit in r: print(hit.path, hit.raw_meta.get('duration'))
"
```

To test Edge TTS standalone:

```bash
python -c "
import asyncio
from pathlib import Path
from creativeforge.adapters.voice.edge_tts import EdgeTtsAdapter
r = asyncio.run(EdgeTtsAdapter().synthesize(
    '역적들을 처단하였사옵니다. 전하께서 소신에게 영의정부사를 내리소서.',
    'ko-KR-InJoonNeural', Path('/tmp/cf-test'), style='stern', item_id='cut03'
))
print(r.path, r.raw_meta)
"
```

## Source-of-truth files (don't lose)

- `/root/.claude/plans/squishy-chasing-oasis.md` — the approved architecture plan (not in repo, exists only in the originating session's filesystem).
- `projects/musinsa-king-choice/CONTEXT.md` + `DECISIONS.md` — the project-level handoff.
- `HANDOFF.md` (this file) — the scaffold-session handoff.

## Original repo

`https://github.com/jackjackjack-coffee/Musinsa-ad-festival` — kept as-is until festival submission completes, then GitHub Archive.
