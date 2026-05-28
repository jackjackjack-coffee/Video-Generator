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
