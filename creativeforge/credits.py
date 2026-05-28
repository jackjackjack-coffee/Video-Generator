"""Google Flow / Gemini video-generation credit accounting.

Gemini AI Pro plan: image generation is unlimited, but video generation draws
from a monthly credit pool (1000 on the Pro plan). Costs below are per *single*
video; generating N variants in one go multiplies by N.

Two generation sources exist and can be mixed to stretch the budget:
  - `flow`   — Google Flow (Veo 3.1 / Omni). Draws from the 1000-credit pool.
  - `gemini` — regular Gemini app (Omni). Tracked separately so Flow credits
               can be conserved for the hero cuts.

Cost table (credits per single video):
  veo-3.1-high-quality : 100   (used for the final hero cuts)
  veo-3.1-fast         :  20
  veo-3.1-lite         :  10
  omni-flash           : duration-dependent — 4s:15  6s:20  8s:25  10s:30
"""

from __future__ import annotations

from typing import Any

# Per-single-video credit cost. A duration-keyed dict means the cost depends on
# clip length (seconds); a flat int means it's fixed regardless of length.
DEFAULT_VIDEO_COSTS: dict[str, int | dict[int, int]] = {
    "veo-3.1-high-quality": 100,
    "veo-3.1-fast": 20,
    "veo-3.1-lite": 10,
    "omni-flash": {4: 15, 6: 20, 8: 25, 10: 30},
}


def cost_per_video(
    model: str | None,
    duration_s: int | None = None,
    costs: dict[str, Any] | None = None,
) -> int:
    """Credits for ONE video of `model`. Unknown/None model (e.g. images) = 0."""
    table = costs or DEFAULT_VIDEO_COSTS
    entry = table.get(model) if model else None
    if entry is None:
        return 0
    if isinstance(entry, dict):
        buckets = sorted(int(k) for k in entry)
        if not buckets:
            return 0
        d = duration_s or buckets[0]
        # Round up to the smallest bucket >= requested duration.
        chosen = next((b for b in buckets if b >= d), buckets[-1])
        return int(entry[chosen])
    return int(entry)


def estimate_item(
    model: str | None,
    variants: int = 1,
    duration_s: int | None = None,
    costs: dict[str, Any] | None = None,
) -> int:
    """Credits to generate `variants` videos of `model`."""
    return cost_per_video(model, duration_s, costs) * max(variants, 1)


def estimate_plan(
    cuts: list[dict],
    default_model: str | None,
    costs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Estimate credits for a list of cut specs.

    Each cut dict may carry `id`, `model`, `variants`, `duration_s`, `source`.
    Returns a breakdown plus totals split by source (flow vs gemini).
    """
    rows: list[dict[str, Any]] = []
    totals: dict[str, int] = {"flow": 0, "gemini": 0}
    for cut in cuts:
        model = cut.get("model") or default_model
        variants = int(cut.get("variants", 1))
        duration_s = cut.get("duration_s")
        source = cut.get("source", "flow")
        credits = estimate_item(model, variants, duration_s, costs)
        totals[source] = totals.get(source, 0) + credits
        rows.append(
            {
                "id": cut.get("id", "?"),
                "model": model,
                "variants": variants,
                "duration_s": duration_s,
                "source": source,
                "credits": credits,
            }
        )
    return {"rows": rows, "totals": totals, "grand_total": sum(totals.values())}
