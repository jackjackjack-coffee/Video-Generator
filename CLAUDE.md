# Operating guide for the generation agent

Standing rules for any Claude Code session driving `creativeforge` (especially
the Phase B Windows session that generates assets against the live Google Flow
UI). Read this before running `s01_cut_images` or `s02_cut_videos`.

## Extend vs. fresh generation (Veo / Flow)

Flow's **Extend** continues an existing clip *from its last frame, in the same
shot* — same subject, camera, lighting, wardrobe. Its only superpower is
**continuity**. It is NOT a scene-change tool.

**Rule of thumb: same shot continuing → Extend. New shot → generate fresh.**

- **Extend when:** one continuous action runs longer than the model's max clip
  length, OR two adjacent moments must read as the *same* unbroken take with zero
  identity/wardrobe drift.
- **Generate fresh when:** any hard cut, new angle/location, new composition, or a
  deliberate tonal/color flip (e.g. the drama→fashion break at cut06). Extend
  inherits the source clip's grade — it can't jump palettes — and gives one
  continuation rather than variants to choose from.
- **This storyboard:** only **cut09** (continuous low-angle march to the gate +
  doors closing) is a real Extend candidate — extend the base clip if 3s isn't
  enough or you want a longer hold on the closing doors. **Never** extend cut05
  into cuts 06/07: those are three distinct shots with a drama→fashion grade
  change; Extend would only produce more of the cut05 crying close-up.
- **Cost:** each Extend bills credits like a normal Veo clip — it buys continuity,
  not budget. Confirm whether Flow exposes Extend on `veo-3.1-fast` vs.
  high-quality only before planning around it.

## Credit strategy: draft-first

Video generation draws from a **1000-credit/month** pool (images are free). Work
in two passes — never spend 100 credits on a prompt you haven't seen rendered:

1. **Draft pass** — every cut on `veo-3.1-fast` (current `02-cut-videos.yaml` =
   180 cr). Review all clips at the approval gate; fix prompts and regen until the
   content/composition is right.
2. **Polish pass** — flip only the approved HERO cuts (01, 05, 06, 07, 09) back to
   `veo-3.1-high-quality` and regen ONLY those via the gate's `[r]` key or
   `creativeforge run musinsa-king-choice --only s02_cut_videos`.

Check the live estimate any time with `creativeforge credits musinsa-king-choice`.
The pipeline warns (does not abort) if a stage estimate would bust the budget.

## Variant selection: keep the best, not the first

Flow renders multiple variants per generation; the adapters download all of them
(`<item>-vN.<ext>`) and default the canonical artifact to v0. At the approval
gate, press **`[v]`** to inspect and promote a different variant to canonical.
This matters most on the **free image stages** (s00/s01) — you already paid
nothing for 4 options, so always pick the strongest before approving.

## Selector iteration (Phase B)

Flow selectors in `creativeforge/browser/flow_imagen.py` / `flow_veo.py` are
first-guess fallback chains. On a miss, `first_visible` dumps
`runs/<id>/debug/<ts>-<label>.{html,png}`. Prepend new candidate lambdas; keep old
ones at the bottom — they self-heal across Flow A/B tests. Never delete a
candidate unless it's verifiably dead.

## Voice strategy: edge-tts (scratch) vs. Voicebox (commercial final)

| Adapter | License | Use for | Requires |
|---------|---------|---------|---------|
| `edge_tts` | Unofficial MS endpoint | Draft / cloud testing | `pip install edge-tts` |
| `voicebox` | Kokoro Apache-2.0 / Chatterbox-Turbo MIT | **Commercial final dub** | Voicebox app running locally |

**To switch to Voicebox for the final commercial dub:**
1. Open `projects/musinsa-king-choice/project.yaml` → `s03_voice`.
2. Comment out `adapter: edge_tts` and uncomment `adapter: voicebox`.
3. Change `voice:` to a Voicebox profile name (browse available profiles at `http://127.0.0.1:17493/docs`).
4. Launch the Voicebox app on your Windows machine.
5. Run `creativeforge run musinsa-king-choice --only s03_voice`.

**Caveats:**
- Do NOT use Voicebox's voice-cloning feature on this ad without written consent from the
  voice owner. Use built-in synthetic profiles only (Kokoro/Chatterbox built-ins).
- Test cut05 ("무진장!" — emotional peak) carefully; pick a profile that can carry the
  tearful-comedic energy. Chatterbox-Turbo handles emotion better than Kokoro for that line.

## Pipeline extensibility: adding AI providers and projects

`creativeforge` is a **model-agnostic, multi-project** pipeline. The project folder
(`projects/musinsa-king-choice/`) defines WHICH adapters to use; the framework doesn't care.

### Switching an AI model (e.g. Veo → Runway for video)

Three steps — no framework changes:

```
1. Write  creativeforge/adapters/video/runway.py
          @register("runway") class RunwayAdapter — implement generate(req, out_dir) -> GenResult

2. Add    "runway": "video"  to ADAPTER_KIND in creativeforge/pipeline.py

3. Change  adapter: runway   in projects/<project>/project.yaml  (one line)
```

The same pattern applies to every stage kind:
- `adapters/image/` for image generation
- `adapters/video/` for video generation
- `adapters/voice/` for TTS
- `adapters/audio/` for music/SFX search
- `adapters/compose/` for final render

You can mix adapters within a project — each stage picks its own via `adapter:` in `project.yaml`.
You can even mix on a per-cut basis using the `adapter:` override inside individual cut YAML items.

### Adding a new project (more Musinsa ads or unrelated videos)

```bash
mkdir projects/musinsa-project-2/
# create project.yaml, storyboard.yaml, prompts/ — same structure as musinsa-king-choice
creativeforge run musinsa-project-2
```

The framework discovers any directory under `projects/` that has a `project.yaml`. No other
registration needed. `creativeforge list` will show it automatically.

### What NEVER changes when you swap models or add projects

- `creativeforge/pipeline.py` core orchestration — untouched
- `creativeforge/state.py`, `config.py`, `cli.py` — untouched
- Approval gate (`ui/approve.py`) — same UX across all adapters
- Credit tracking (`credits.py`) — add a new model's cost to the table if needed
