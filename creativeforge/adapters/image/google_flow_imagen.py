"""Google Flow Imagen adapter — drives labs.google/fx/tools/flow via Playwright.

Browser interaction lives in `creativeforge/browser/flow_imagen.py`. This file
is a thin Protocol-conformant wrapper that opens a headed context and hands
the Page to the helper.

First login: run `python scripts/login_google_flow.py` once to populate
`.auth/chrome-profile/` and `.auth/google.json`.
"""

from __future__ import annotations

from pathlib import Path

from creativeforge.adapters.base import GenRequest, GenResult, register
from creativeforge.browser.flow_imagen import generate_image
from creativeforge.browser.session import headed_context
from creativeforge.config import BrowserConfig


@register("google_flow_imagen")
class GoogleFlowImagenAdapter:
    name: str

    def __init__(
        self,
        browser_cfg: BrowserConfig | None = None,
        project_dir: Path | None = None,
    ):
        self.browser_cfg = browser_cfg or BrowserConfig()
        self.project_dir = project_dir or Path(".")

    async def generate(self, req: GenRequest, out_dir: Path) -> GenResult:
        storage_state = self._resolve(self.browser_cfg.storage_state)
        user_data_dir = self._resolve(self.browser_cfg.user_data_dir)
        async with headed_context(
            storage_state=storage_state,
            user_data_dir=user_data_dir,
        ) as ctx:
            page = await ctx.new_page()
            return await generate_image(page, req, out_dir)

    def _resolve(self, value: str | None) -> Path | None:
        if not value:
            return None
        p = Path(value)
        if not p.is_absolute():
            p = (self.project_dir / value).resolve()
        return p
