"""Persistent Playwright browser session with storage_state for Google login reuse.

Google blocks OAuth sign-in from browsers that advertise automation ("이 브라우저
또는 앱이 안전하지 않을 수 있습니다" / "this browser or app may not be secure").
To log into your own account for your own authorized use, we launch your real
installed Chrome (channel="chrome") with the automation signals suppressed:

  - ignore_default_args=["--enable-automation"]   → drops the automation banner/flag
  - --disable-blink-features=AutomationControlled → makes navigator.webdriver false

If real Chrome isn't installed we fall back to Playwright's bundled Chromium with
the same stealth args (less reliable against Google's check, but better than the
default).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from playwright.async_api import BrowserContext, async_playwright

# Args that make a Playwright-driven browser look like a normal user browser.
_STEALTH_ARGS = ["--disable-blink-features=AutomationControlled"]
_IGNORE_DEFAULT_ARGS = ["--enable-automation"]


@asynccontextmanager
async def headed_context(
    storage_state: Path | None,
    user_data_dir: Path | None = None,
    viewport: tuple[int, int] = (1280, 900),
):
    """Yield a Playwright BrowserContext.

    Prefer user_data_dir (persistent profile) for real Google login. Falls back
    to storage_state JSON if profile dir not provided. Tries real Chrome first,
    then bundled Chromium.
    """
    async with async_playwright() as pw:
        if user_data_dir is not None:
            user_data_dir.mkdir(parents=True, exist_ok=True)
            context = await _persistent_with_fallback(pw, user_data_dir)
        else:
            browser = await _launch_with_fallback(pw)
            context = await browser.new_context(
                storage_state=str(storage_state) if storage_state and storage_state.exists() else None,
                viewport={"width": viewport[0], "height": viewport[1]},
            )
        # Belt-and-suspenders: also strip navigator.webdriver via an init script,
        # in case the launch flag isn't honored on a given Chrome build.
        try:
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
        except Exception:
            pass
        try:
            yield context
        finally:
            if storage_state is not None and user_data_dir is None:
                storage_state.parent.mkdir(parents=True, exist_ok=True)
                await context.storage_state(path=str(storage_state))
            await context.close()


async def _persistent_with_fallback(pw, user_data_dir: Path) -> BrowserContext:
    """Persistent context using real Chrome if available, else bundled Chromium."""
    kwargs = dict(
        user_data_dir=str(user_data_dir),
        headless=False,
        no_viewport=True,  # natural window size — looks like a real user
        args=_STEALTH_ARGS,
        ignore_default_args=_IGNORE_DEFAULT_ARGS,
    )
    try:
        return await pw.chromium.launch_persistent_context(channel="chrome", **kwargs)
    except Exception as e:
        print(f"[session] real Chrome unavailable ({e}); falling back to bundled Chromium.")
        return await pw.chromium.launch_persistent_context(**kwargs)


async def _launch_with_fallback(pw):
    """Non-persistent browser using real Chrome if available, else bundled Chromium."""
    kwargs = dict(
        headless=False,
        args=_STEALTH_ARGS,
        ignore_default_args=_IGNORE_DEFAULT_ARGS,
    )
    try:
        return await pw.chromium.launch(channel="chrome", **kwargs)
    except Exception as e:
        print(f"[session] real Chrome unavailable ({e}); falling back to bundled Chromium.")
        return await pw.chromium.launch(**kwargs)
