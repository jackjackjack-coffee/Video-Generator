"""Persistent Playwright browser session with storage_state for Google login reuse."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from playwright.async_api import BrowserContext, async_playwright


@asynccontextmanager
async def headed_context(
    storage_state: Path | None,
    user_data_dir: Path | None = None,
    viewport: tuple[int, int] = (1280, 900),
):
    """Yield a Playwright BrowserContext.

    Prefer user_data_dir (persistent Chrome profile) for real Google login. Falls back
    to storage_state JSON if profile dir not provided.
    """
    async with async_playwright() as pw:
        if user_data_dir is not None:
            user_data_dir.mkdir(parents=True, exist_ok=True)
            context: BrowserContext = await pw.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=False,
                viewport={"width": viewport[0], "height": viewport[1]},
            )
        else:
            browser = await pw.chromium.launch(headless=False)
            context = await browser.new_context(
                storage_state=str(storage_state) if storage_state and storage_state.exists() else None,
                viewport={"width": viewport[0], "height": viewport[1]},
            )
        try:
            yield context
        finally:
            if storage_state is not None and user_data_dir is None:
                storage_state.parent.mkdir(parents=True, exist_ok=True)
                await context.storage_state(path=str(storage_state))
            await context.close()
