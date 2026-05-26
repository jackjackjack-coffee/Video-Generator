"""Microsoft Edge TTS adapter.

Uses the `edge-tts` PyPI package, which speaks to the public Edge TTS endpoint.
Free, no API key. SSML supported for prosody/pitch tweaks (useful for 사극 tone).

Note: This is an unofficial endpoint. If MS changes auth, swap to Clova or ElevenLabs
by editing project.yaml `voice.adapter`.
"""

from __future__ import annotations

import re
from pathlib import Path

import edge_tts

from creativeforge.adapters.base import GenResult, register


def _slug(item_id: str | None, text: str) -> str:
    base = item_id or re.sub(r"[^a-zA-Z0-9가-힣]+", "_", text.strip())[:32]
    return base or "voice"


@register("edge_tts")
class EdgeTtsAdapter:
    name: str

    DEFAULT_VOICE = "ko-KR-InJoonNeural"

    # SSML wrappers for stylistic tones. Sajǔk (사극) = pitch down + slower rate.
    STYLE_SSML: dict[str, dict[str, str]] = {
        "stern": {"pitch": "-10%", "rate": "-8%"},
        "tearful": {"pitch": "-5%", "rate": "-15%"},
        "comic": {"pitch": "+8%", "rate": "+10%"},
        "royal": {"pitch": "-12%", "rate": "-10%"},
    }

    async def synthesize(
        self,
        text: str,
        voice: str,
        out_dir: Path,
        style: str | None = None,
        item_id: str | None = None,
    ) -> GenResult:
        out_dir.mkdir(parents=True, exist_ok=True)
        voice_name = voice or self.DEFAULT_VOICE

        rate = "+0%"
        pitch = "+0Hz"
        if style and style in self.STYLE_SSML:
            cfg = self.STYLE_SSML[style]
            rate = cfg["rate"]
            pitch = cfg["pitch"]

        # edge-tts accepts rate/pitch directly (not raw SSML required).
        communicate = edge_tts.Communicate(text=text, voice=voice_name, rate=rate, pitch=pitch)

        dest = out_dir / f"{_slug(item_id, text)}.mp3"
        await communicate.save(str(dest))

        return GenResult(
            path=dest,
            model_used=f"edge-tts/{voice_name}",
            raw_meta={"style": style, "rate": rate, "pitch": pitch, "text_len": len(text)},
        )
