"""Google Flow Imagen adapter — STUB.

Implements the interface so the pipeline wires up, but the actual Playwright flow
is unimplemented because writing reliable selectors requires interactive iteration
with the live UI (headed Chromium + DevTools).

# Implementation checklist for the next session

1. **Health check & login**:
   - Open https://labs.google/flow (or current Flow URL).
   - Detect logged-in state via avatar role/text.
   - On failure: pause with rich prompt "Sign in manually, then press Enter."

2. **Navigation**:
   - Click "Create" → "Image" (Imagen 4 / Imagen 4 Ultra).
   - Set aspect ratio to req.aspect_ratio (default 9:16).
   - Set model to req.model (e.g. "imagen-4-ultra").

3. **Reference upload (for character-consistent cuts)**:
   - For each path in req.references, upload via the reference image button.

4. **Prompt + submit**:
   - Fill prompt textarea with req.prompt.
   - Click Generate.

5. **Wait for completion**:
   - Watch for result grid (DOM mutation observer or `expect(card).to_be_visible(timeout=600_000)`).
   - 4 variants typically appear. Pick the first or surface all to the approval gate.

6. **Download**:
   - Hover variant → click download button → `page.expect_download()`.
   - Save to `out_dir / f"{req.extra['item_id']}.png"`.

7. **Defense**:
   - All clicks via selector fallback chain (role first, css second).
   - On selector miss → dump HTML to runs/<id>/debug/.

# Useful refs

- creativeforge.browser.session for storage_state-backed login persistence.
- creativeforge.browser.selectors for the fallback locator pattern.
"""

from __future__ import annotations

from pathlib import Path

from creativeforge.adapters.base import GenRequest, GenResult, register


@register("google_flow_imagen")
class GoogleFlowImagenAdapter:
    name: str

    async def generate(self, req: GenRequest, out_dir: Path) -> GenResult:
        raise NotImplementedError(
            "google_flow_imagen Playwright flow is not implemented yet. "
            "See module docstring for the implementation checklist."
        )
