"""Google Flow Veo adapter — STUB.

# Implementation checklist for the next session

1. Reuse browser session module (storage_state).
2. Navigate to Flow → Video creation.
3. Select model from req.model (e.g. "veo-3.1-high-quality" — match exact UI label).
4. Image-to-video: upload req.references[0] as the start frame (or grid of refs).
5. Aspect ratio = req.aspect_ratio.
6. Prompt = req.prompt.
7. Submit. Wait for completion (3-5 min typical; cap at 10 min).
   - Poll via DOM, not sleep.
   - Show progress text if available.
8. Download mp4 → out_dir / f"{req.extra['item_id']}.mp4".
9. On credit_exhausted error: raise CreditExhausted(...) so pipeline can fall back.

# Known quirks (from manual experience documented in projects/musinsa-king-choice/CONTEXT.md)

- Veo 3.1 clip max 8 seconds. Longer cuts must be stitched (storyboard.yaml controls this — keep each cut ≤ 8s in this project).
- Image-to-video preserves identity better than text-only — always pass the cut01 still image as reference.
- "high quality" toggle costs ~3x credits but is required for visible quality on 1080p output.
"""

from __future__ import annotations

from pathlib import Path

from creativeforge.adapters.base import GenRequest, GenResult, register


@register("google_flow_veo")
class GoogleFlowVeoAdapter:
    name: str

    async def generate(self, req: GenRequest, out_dir: Path) -> GenResult:
        raise NotImplementedError(
            "google_flow_veo Playwright flow is not implemented yet. "
            "See module docstring for the implementation checklist."
        )
