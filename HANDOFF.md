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

### HIGH PRIORITY — the one remaining blocker

1. **Phase B: paired selector iteration** (Windows, local Claude Code session).
   - Bootstrap: `python scripts/login_google_flow.py`.
   - Test target: `creativeforge run musinsa-king-choice --only s00_character_sheets --auto-approve`.
   - First-guess selectors are committed but will mostly miss. Each miss dumps `runs/<id>/debug/<ts>-<label>.{html,png}`. Iterate by prepending new candidate lambdas in `creativeforge/browser/flow_imagen.py` and `flow_veo.py`. Keep older candidates at the bottom — they self-heal across Flow A/B tests.
   - Tools: `playwright codegen https://labs.google/fx/tools/flow --load-storage .auth/google.json`, `set PWDEBUG=1`.
   - Process screenshots auto-save to `runs/<id>/process-doc/` — no manual work needed.
   - When Phase B is done, run `creativeforge process-doc <run_id> --html` to compile evidence for contest submission.

   - **Operating rules live in `CLAUDE.md`** (auto-loaded each session): Extend vs.
     fresh generation, draft-first credit strategy, variant selection, voice
     strategy, and the model/project extensibility recipes. Read it before
     `s01_cut_images` / `s02_cut_videos`.

   **Order of operations on Windows:**
   1. `python scripts/login_google_flow.py` (one-time).
   2. `creativeforge run musinsa-king-choice --only s00_character_sheets` → iterate
      selectors until it generates (prepend fixed selectors; check `runs/<id>/debug/`).
   3. Then `s01_cut_images`, then `s02_cut_videos` (draft pass on veo-3.1-fast).
   4. Review at the gate, regen prompts, polish HERO cuts to high-quality.
   5. Voice: runs on edge_tts by default. For the **final commercial dub**, install
      the Voicebox app, flip `adapter: voicebox` in `project.yaml`, re-run
      `--only s03_voice`, and **listen to the Korean output** (esp. cut05).
   6. `s04_audio` (Pixabay, needs `PIXABAY_API_KEY`), then `s05_compose` (Remotion).
   7. `creativeforge process-doc <run_id> --html` for submission evidence.

### DONE (completed in session 2026-05-28)

2. ✅ **Regen loop** — `[r]` / `[e]` in the approval gate now actually re-dispatches flagged items inline and re-prompts. Tested with 11 unit tests.
3. ✅ **`resume <run_id>`** — fully implemented: loads `state.json`, derives first non-approved stage from topo order, resumes from there.
4. ✅ **`doctor` health checks** — extended with PIXABAY_API_KEY, edge_tts, npm/npx, `.auth/google.json`, `.auth/chrome-profile/` rows.
5. ✅ **Audio query fix** — `04-audio-keywords.yaml` restructured into `bgm_traditional / bgm_bright / sfx` groups with `queries:` lists. Pixabay no longer receives style notes like `"60~80 BPM"`.
6. ✅ **Visual style consistency** — `project.yaml` now has `visual_style.drama` / `visual_style.fashion` color-grade suffixes. All 9 cut prompts are tagged `style: drama` (cuts 01-05) or `style: fashion` (cuts 06-09). The pipeline appends the suffix automatically.
7. ✅ **Process screenshots** — `capture_process_shot` added to `selectors.py`; `flow_imagen.py` and `flow_veo.py` capture 3 screenshots per item (ui-ready, prompt-entered, generated). `creativeforge process-doc <run_id> [--html] [--pdf]` compiles them for contest submission.
8. ✅ **Reference ID normalization** — sheet IDs normalized to ASCII slugs (`sheet1-danjong-royal` etc.); `_resolve_references` tries exact-slug match first, then falls back to digit glob.
9. ✅ **Cut image refs in s02_cut_videos** — each video item now references its matching cut image as start-frame (much better Veo quality).
10. ✅ **Credit budgeting** (Gemini AI Pro = 1000 video credits/month; images unlimited).
    - `creativeforge/credits.py` — cost table (veo-3.1-high-quality 100, fast 20, lite 10; omni-flash 4s:15/6s:20/8s:25/10s:30 per video) × variant count.
    - Per-cut `model` / `variants` / `duration_s` / `source` in `02-cut-videos.yaml`. **Draft-first**: all 9 cuts start on `veo-3.1-fast` = **180 cr** (see `CLAUDE.md`); flip the 5 HERO cuts to high-quality on the polish pass.
    - `creativeforge credits musinsa-king-choice` prints the per-cut breakdown + remaining budget.
    - Pipeline prints the stage estimate before s02 and a running `+N credits` after each video; `state.json` tracks `credits_used` split by source. Over-budget prints a red warning (does not abort).
    - `source: gemini` marks a cut as generated via the regular Gemini app (Omni) — tracked in a **separate** pool so the 1000 Flow credits are conserved. The Gemini-Omni adapter itself is future work (no selectors yet); the budget plumbing is ready for it.
11. ✅ **Draft-first credits** — all 9 cuts default to `veo-3.1-fast` (180 cr); HERO cuts upgrade to high-quality on a polish pass. Rule documented in `CLAUDE.md`.
12. ✅ **Variant picker** — `GenResult.variant_paths`; Flow adapters download every rendered variant; approval gate `[v]` key + `select_variant` promote the chosen one to canonical. Biggest win on the free image stages.
13. ✅ **`CLAUDE.md`** — agent operating guide (Extend rule, draft-first, variant pick, selector iteration) auto-loaded each session.
14. ✅ **Voicebox TTS adapter** — `creativeforge/adapters/voice/voicebox.py`, `@register("voicebox")`, REST call to `http://127.0.0.1:17493/generate`. Commercial-clean (Kokoro Apache-2.0 / Chatterbox-Turbo MIT) vs. edge-tts's unofficial endpoint. `edge_tts` stays the **default** (cloud/CI runnable); flip `adapter: voicebox` in `project.yaml` for the final dub on Windows. `doctor` pings the app (WARN if not running). s03_voice prints a switch reminder when still on edge_tts. 3 new tests.
15. ✅ **Pipeline extensibility documented** — `CLAUDE.md` now spells out the model-swap recipe (new adapter file + 1 `ADAPTER_KIND` line + 1 `project.yaml` line; Veo→Runway and edge-tts→ElevenLabs examples) and the add-a-project recipe (new folder under `projects/`, zero framework changes).

### Commercial-use status (resolved 2026-05-28)
- **Video (Veo/Flow):** user is on a **paid Google AI Pro plan** → commercial use of Veo output is covered. ✅
- **Voice:** edge-tts = scratch only (unofficial endpoint, not cleared). Final dub must use **Voicebox** (Kokoro/Chatterbox). ⚠️ **Korean quality is unverified** — judge by ear on Windows; if neither engine carries the emotional cut05 line ("무진장!"), fall back to ElevenLabs (paid, strong Korean, same 3-step adapter swap). Never voice-clone a real person without written consent.

### Credit-related follow-ups for Phase B / later
- The Veo adapter's `_select_output_count` (variants) is a first-guess selector stub — refine it live like the other Flow selectors.
- If you decide to offload cuts to the regular Gemini app, write a `gemini_omni` video adapter and register it; set those cuts to `source: gemini` + `model: omni-flash`.

### Low priority / v2

- Approval gate web UI (FastAPI + simple HTML) — easier preview than `xdg-open`.
- Parallel item generation within a stage.
- `scripts/new_project.py` wizard for project #2+.

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
