"""Voicebox TTS adapter.

Voicebox (github.com/jamiepine/voicebox, MIT) is a local GUI voice studio that
exposes a REST API on 127.0.0.1:17493. It wraps Kokoro (Apache-2.0) and
Chatterbox-Turbo (MIT) — both commercially licensed — making it safe for the
Musinsa ad festival entry.

Usage:
  1. Install and launch the Voicebox app on your Windows machine.
  2. In project.yaml, change `adapter: edge_tts` → `adapter: voicebox` for s03_voice.
  3. Set `voice:` to a Voicebox profile name (e.g. "af_heart", "bf_emma").
  4. Run `creativeforge run musinsa-king-choice --only s03_voice`.

The base URL can be overridden via the VOICEBOX_URL environment variable.
"""

from __future__ import annotations

import mimetypes
import re
from pathlib import Path

import httpx

from creativeforge.adapters.base import GenResult, register

_BASE_URL = None  # resolved lazily so env var can be set after import


def _get_base() -> str:
    import os
    return os.environ.get("VOICEBOX_URL", "http://127.0.0.1:17493").rstrip("/")


def _slug(item_id: str | None, text: str) -> str:
    base = item_id or re.sub(r"[^a-zA-Z0-9가-힣]+", "_", text.strip())[:32]
    return base or "voice"


@register("voicebox")
class VoiceboxAdapter:
    name: str

    DEFAULT_LANGUAGE = "ko"

    async def _generate_audio(self, text: str, voice: str, language: str) -> tuple[bytes, str]:
        """POST to Voicebox /generate and return (audio_bytes, file_extension).

        Handles two possible response shapes:
        - audio/*, application/octet-stream → raw bytes in response body
        - JSON with a path/url/audio field → fetch or read that resource
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{_get_base()}/generate",
                json={"text": text, "profile": voice, "language": language},
            )
            resp.raise_for_status()

            ct = resp.headers.get("content-type", "")
            if ct.startswith("audio/") or ct in ("application/octet-stream",):
                ext = mimetypes.guess_extension(ct.split(";")[0].strip()) or ".wav"
                return resp.content, ext

            # JSON response — look for a path or URL to the audio file
            data = resp.json()
            audio_url: str | None = data.get("url") or data.get("audio")
            audio_path: str | None = data.get("path")

            if audio_url:
                audio_resp = await client.get(audio_url)
                audio_resp.raise_for_status()
                ct2 = audio_resp.headers.get("content-type", "audio/wav")
                ext = mimetypes.guess_extension(ct2.split(";")[0].strip()) or ".wav"
                return audio_resp.content, ext

            if audio_path:
                file_bytes = Path(audio_path).read_bytes()
                ext = Path(audio_path).suffix or ".wav"
                return file_bytes, ext

            raise ValueError(f"Voicebox response had no audio payload: {data}")

    async def synthesize(
        self,
        text: str,
        voice: str,
        out_dir: Path,
        style: str | None = None,
        item_id: str | None = None,
    ) -> GenResult:
        out_dir.mkdir(parents=True, exist_ok=True)
        language = self.DEFAULT_LANGUAGE

        audio_bytes, ext = await self._generate_audio(text, voice, language)

        slug = _slug(item_id, text)
        if not ext.startswith("."):
            ext = f".{ext}"
        dest = out_dir / f"{slug}{ext}"
        dest.write_bytes(audio_bytes)

        return GenResult(
            path=dest,
            model_used=f"voicebox/{voice}",
            raw_meta={
                "style": style,
                "language": language,
                "engine": "voicebox",
                "text_len": len(text),
            },
        )
