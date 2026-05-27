"""Google Flow Veo adapter — drives labs.google/fx/tools/flow via Playwright.

Browser interaction lives in `creativeforge/browser/flow_veo.py`. Same shape as
the Imagen adapter.

Known quirks (from projects/musinsa-king-choice/CONTEXT.md):
- Veo 3.1 clip max ~8s. Storyboard must keep each cut ≤ 8s.
- Image-to-video preserves identity better than text-only — always pass a
  reference image. The pipeline auto-resolves references for s02_cut_videos
  from s01_cut_images outputs.
- The 'high quality' toggle costs ~3x credits but is required for 1080p output.
"""

from __future__ import annotations

from pathlib import Path

from creativeforge.adapters.base import GenRequest, GenResult, register
from creativeforge.browser.flow_veo import generate_video
from creativeforge.browser.session import headed_context
from creativeforge.config import BrowserConfig


@register("google_flow_veo")
class GoogleFlowVeoAdapter:
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
            return await generate_video(page, req, out_dir)

    def _resolve(self, value: str | None) -> Path | None:
        if not value:
            return None
        p = Path(value)
        if not p.is_absolute():
            p = (self.project_dir / value).resolve()
        return p
