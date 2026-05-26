# HANDOFF — creativeforge initial scaffold

> Picked up by the next session. Read this first.

## What this is

`creativeforge` is a multi-project AI video production pipeline extracted from the standalone `Musinsa-ad-festival` repo. The first resident project is `projects/musinsa-king-choice/` — the 무신사 무진장 광고제 2026 출품작 "왕의 선택" (30s, 9:16).

Design and rationale: see the approved plan referenced in the commit body, summarized in `README.md`.

## What was done in the scaffold session (2026-05-26)

- Repo structure + Python package skeleton (`pyproject.toml`, `creativeforge/` package, `projects/`, `runs/`, `scripts/`, `tests/`).
- Core abstractions: `creativeforge/config.py` (ProjectConfig), `creativeforge/state.py` (RunState), `creativeforge/stages/base.py` (Stage), `creativeforge/adapters/base.py` (Protocols + registry).
- CLI skeleton: `creativeforge/cli.py` — `list`, `doctor`, `run --dry-run`, `resume`. `list` and `doctor` work end-to-end; `run` only prints the stage table (no orchestration yet).
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

## What's NOT done — picked-up tasks

### High priority (blocks pipeline running real)

1. **Implement `pipeline.py`** (`creativeforge/pipeline.py`).
   - Iterate stages in dependency order.
   - For each stage: list items (from `prompts_file` `items` map or storyboard cuts), dispatch to adapter, write artifacts to `runs/<id>/stage-NN/<item>.ext` + `.meta.json`.
   - Between stages: call `ui/approve.py` (also TODO).
   - Persist `state.json` after every item.

2. **Implement `ui/approve.py`** — interactive `[a/r/e/i/s/q]` gate with rich table + OS preview (`xdg-open` / `open`). $EDITOR integration for `[e]` prompt edits → store override in `runs/<id>/prompt-overrides/<item>.yaml`.

3. **Implement Playwright adapters** (`google_flow_imagen.py`, `google_flow_veo.py`).
   - Live UI exploration session required: headed Chromium, use DevTools to map selectors.
   - Use `creativeforge.browser.session.headed_context` for persistence.
   - Follow the checklists in each adapter's module docstring.
   - **Caution**: don't try to solve captchas; let the user clear them manually.

### Medium priority

4. Hand-edit `projects/musinsa-king-choice/CONTEXT.md` and `DECISIONS.md` — they're auto-generated drafts. Verify the "current progress" section against reality.
5. Review `projects/musinsa-king-choice/storyboard.yaml` — speaker tags were manually corrected for cut04 (danjong) and cut09 (danjong), plus dialogue text fixed to "숙부, 어찌하여…". Other cuts looked fine on a quick check but a full pass against the original PLAN.md cuts table is still worth doing.
6. Normalize reference IDs in `prompts/01-cut-images.yaml` and `prompts/02-cut-videos.yaml`. Currently they read `Sheet 3 (Suyang)`; should map to actual sheet IDs like `sheet3-prince-suyang-수양대군` (or simpler IDs after a slug cleanup pass).
7. Sheet IDs in `prompts/00-character-sheets.yaml` carry Korean in the slug (`sheet1-king-danjong-조선-왕복-버전`). Decide: normalize to `sheet1-danjong-royal`, `sheet2-danjong-modern`, etc. and update reference fields throughout.
8. Add `--only <stage>` and `--from <stage>` flags to `creativeforge run` once orchestration exists.

### Low priority / v2

9. `creativeforge doctor` should check adapter health (PIXABAY_API_KEY present, edge-tts reachable, npm/remotion present).
10. Approval gate web UI (FastAPI + simple HTML) — easier preview than `xdg-open`.
11. Parallel item generation within a stage.
12. AI-process auto-capture → PDF for festival submission.

## How to verify what works right now

```bash
cd Video-Generator
pip install -e .
creativeforge doctor          # lists 5 registered adapters
creativeforge list            # shows musinsa-king-choice
creativeforge run musinsa-king-choice --dry-run   # prints stage table, no execution
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
