# creativeforge

Multi-project AI video production pipeline. Stage-gated, pluggable adapters, designed for video ad festivals and similar short-form deliverables.

**First resident project**: `projects/musinsa-king-choice/` — 무신사 무진장 광고제 2026 출품작 "왕의 선택" (30초, 9:16). Migrated from the standalone `Musinsa-ad-festival` repo. See `projects/musinsa-king-choice/CONTEXT.md` for current status.

## Why

Same video-production work was repeated by hand:
- Click through Google Flow Imagen / Veo UIs for every cut.
- Re-build Remotion code for every new project.
- Lose context between sessions because everything was prose in `PLAN.md`.

creativeforge separates **reusable core** (pipeline, adapters, CLI) from **project data** (prompts, storyboards, Remotion code) so adding a second ad festival is a matter of dropping a new `projects/<name>/` folder.

## Architecture

```
creativeforge/                   # reusable core package
  cli.py                         # `creativeforge run | resume | list | doctor`
  pipeline.py                    # stage orchestration + approval gate
  config.py                      # ProjectConfig (pydantic)
  state.py                       # runs/<id>/state.json
  stages/                        # s00..s05 stage logic
  adapters/                      # interfaces + implementations
    base.py                      # ImageAdapter, VideoAdapter, VoiceAdapter, ...
    image/google_flow_imagen.py  # Playwright (stub — see code)
    video/google_flow_veo.py     # Playwright (stub)
    voice/edge_tts.py            # HTTP (Microsoft Edge TTS)
    voice/clova.py               # HTTP (Naver Clova)
    audio/pixabay.py             # HTTP API
    compose/remotion.py          # subprocess wrapper
  browser/                       # Playwright session, selectors, waits
  ui/approve.py                  # [a/r/e/i/s/q] approval gate

projects/
  musinsa-king-choice/
    project.yaml                 # adapter + model selection
    CONTEXT.md                   # MUST-READ for any new session
    DECISIONS.md                 # timestamped decision log
    prompts/                     # 00..04 yaml prompts
    storyboard.yaml              # cuts + subtitles
    branding/                    # logos, KV
    references/                  # character sheets
    remotion/                    # this project's Remotion code

runs/<run_id>/                   # execution artifacts (gitignored)
  state.json
  stage-NN-*/                    # artifacts + meta.json + attempts/
```

## Current status

This is an **initial scaffold**. Working:
- Repository structure and Python package skeleton.
- `creativeforge.config`, `creativeforge.state`, `creativeforge.stages.base`, `creativeforge.adapters.base`.
- Migration script: `scripts/import_musinsa.py` — converts the existing `Musinsa-ad-festival` repo into `projects/musinsa-king-choice/`.
- Pixabay, Edge TTS, Remotion adapters: implemented (HTTP / subprocess).
- Google Flow Imagen, Veo adapters: **stub only** with detailed TODO. Need iterative work with a real browser session to write selectors.

Not working yet:
- CLI is skeletal (no real `run` execution wired through).
- Approval gate UX is sketched but not interactive.
- Tests are placeholders.

See `HANDOFF.md` for the picked-up-by-the-next-session brief.

## License

Internal / private project. No public license set.
