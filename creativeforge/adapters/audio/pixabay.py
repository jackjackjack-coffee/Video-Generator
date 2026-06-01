"""Pixabay music search and download.

API docs: https://pixabay.com/api/docs/ (music endpoint is /api/music/). Pixabay
license allows commercial use without attribution.

Music-only by design: diegetic SFX now comes from Veo native audio, and the single
non-diegetic title-card impact is a bundled Remotion asset. The ``kind`` parameter is
kept for Protocol compatibility but ``"sfx"`` is rejected (see ``search_and_pick``).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import httpx

from creativeforge.adapters.base import GenResult, register


@register("pixabay")
class PixabayAdapter:
    name: str
    API_BASE = "https://pixabay.com/api/music/"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("PIXABAY_API_KEY", "")
        if not self.api_key:
            raise RuntimeError(
                "PIXABAY_API_KEY missing. Set it in .env or pass api_key= to PixabayAdapter."
            )

    async def search_and_pick(
        self,
        query: str,
        kind: Literal["music", "sfx"],
        duration_s: tuple[int, int] | None,
        out_dir: Path,
        top_k: int = 5,
    ) -> list[GenResult]:
        if kind == "sfx":
            raise ValueError(
                "Pixabay SFX search was removed. Diegetic SFX comes from Veo native "
                "audio; the non-diegetic title-card impact is a bundled Remotion asset "
                "(remotion/public/sfx-bundled/impact.mp3)."
            )
        out_dir.mkdir(parents=True, exist_ok=True)

        params: dict[str, str | int] = {
            "key": self.api_key,
            "q": query,
            "per_page": max(top_k, 3),
            "safesearch": "true",
        }
        if duration_s is not None:
            params["min_duration"] = duration_s[0]
            params["max_duration"] = duration_s[1]

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(self.API_BASE, params=params)
            r.raise_for_status()
            payload = r.json()

        hits = payload.get("hits", [])[:top_k]
        results: list[GenResult] = []
        async with httpx.AsyncClient(timeout=120) as client:
            for hit in hits:
                audio_url = hit.get("audio") or hit.get("preview")
                if not audio_url:
                    continue
                fname = f"{query.replace(' ', '_')}__{hit['id']}.mp3"
                dest = out_dir / fname
                resp = await client.get(audio_url)
                resp.raise_for_status()
                dest.write_bytes(resp.content)
                results.append(
                    GenResult(
                        path=dest,
                        source_url=hit.get("pageURL"),
                        model_used="pixabay-music-api",
                        raw_meta={
                            "id": hit.get("id"),
                            "duration": hit.get("duration"),
                            "tags": hit.get("tags"),
                            "user": hit.get("user"),
                            "kind": kind,
                        },
                    )
                )
        return results
