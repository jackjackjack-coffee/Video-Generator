"""Selector resilience for Flow's evolving UI.

Each high-level action (model pick, prompt fill, etc.) is expressed as a list of
candidate locators. `first_visible` returns whichever candidate appears first,
giving us a graceful fallback chain (role → text → CSS → ad-hoc). When every
candidate misses, we dump the current DOM + a screenshot so the user can paste
the relevant snippet back and we extend the chain.
"""

from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable

from playwright.async_api import Locator, Page

# Set by Pipeline._dispatch right before calling adapter.generate(). The selector
# helpers below read it so debug dumps land in the right run dir without each
# adapter having to thread the path through.
CURRENT_RUN_DIR: ContextVar[Path | None] = ContextVar("CURRENT_RUN_DIR", default=None)


LocatorFactory = Callable[[Page], Locator]


class SelectorMiss(RuntimeError):
    """Raised when no candidate locator becomes visible. Carries the dump path."""

    def __init__(self, label: str, dump_path: Path | None) -> None:
        super().__init__(f"selector miss: {label} (debug: {dump_path})")
        self.label = label
        self.dump_path = dump_path


class LoginRequired(RuntimeError):
    """Raised when Flow shows a logged-out state. User must rerun login script."""

    def __init__(self) -> None:
        super().__init__(
            "Not logged into Google Flow. Run: python scripts/login_google_flow.py"
        )


async def first_visible(
    page: Page,
    candidates: list[LocatorFactory],
    *,
    timeout_ms: int = 8000,
    label: str = "?",
) -> Locator:
    """Return the first candidate that becomes visible within timeout.

    Each candidate gets a fair slice of the total timeout. Older / less-precise
    candidates can stay at the bottom of the list — they're cheap and they
    self-heal across Flow UI A/B tests.
    """
    per_attempt = max(timeout_ms // max(len(candidates), 1), 500)
    last_error: Exception | None = None
    for factory in candidates:
        try:
            loc = factory(page).first
            await loc.wait_for(state="visible", timeout=per_attempt)
            return loc
        except Exception as e:
            last_error = e
            continue
    dump = await dump_debug(page, label)
    raise SelectorMiss(label, dump) from last_error


async def dump_debug(page: Page, label: str) -> Path | None:
    """Write `<run_dir>/debug/<ts>-<label>.{html,png}`. Best-effort."""
    run_dir = CURRENT_RUN_DIR.get()
    base = (run_dir or Path(".tmp")) / "debug"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%H%M%S")
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)[:40]
    html_path = base / f"{ts}-{safe}.html"
    png_path = base / f"{ts}-{safe}.png"
    try:
        html_path.write_text(await page.content(), encoding="utf-8")
        await page.screenshot(path=str(png_path), full_page=True)
    except Exception:
        pass
    return html_path
