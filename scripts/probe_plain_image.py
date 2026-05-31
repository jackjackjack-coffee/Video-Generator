"""Exploration probe: find Flow's PLAIN (non-agent) image-generation path.

Flow's 2026 agent mode (새 프로젝트 → chat thread) fails to generate Imagen 4
server-side. Plain image generation still works manually, so the adapter must
drive that classic path instead. This probe opens Flow with the logged-in
profile and dumps candidates + screenshots at each step so we can map it:

  1. initial landing
  2. the 도구 (Tools) section
  3. (best-effort) a text-to-image / image tool entry

Read-only exploration: never submits a prompt, never spends credits. Leaves the
browser open at the end so the path can be inspected by hand.

Usage:
    python scripts/probe_plain_image.py
"""

from __future__ import annotations

import asyncio
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Korean Windows console is cp949; model names contain emoji (🍌) and Korean.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass

from creativeforge.browser.selectors import CURRENT_RUN_DIR, dump_debug  # noqa: E402
from creativeforge.browser.session import headed_context  # noqa: E402

PROFILE_DIR = REPO_ROOT / ".auth" / "chrome-profile"
STORAGE_STATE = REPO_ROOT / ".auth" / "google.json"
FLOW_URL = "https://labs.google/fx/tools/flow"


async def _dump(page, label: str) -> None:
    """Screenshot + HTML + candidates inventory for one step."""
    path = await dump_debug(page, label)
    print(f"[probe] dumped {label} → {path}")


async def _try_click(page, label: str, candidates) -> bool:
    """Click the first visible candidate; return True if clicked."""
    for factory in candidates:
        try:
            loc = factory(page).first
            await loc.wait_for(state="visible", timeout=3000)
            await loc.click()
            print(f"[probe] clicked: {label}")
            return True
        except Exception:
            continue
    print(f"[probe] NOT found: {label}")
    return False


async def main() -> int:
    run_dir = REPO_ROOT / "runs" / f"probe-plain-image-{datetime.now():%Y%m%d-%H%M%S}"
    (run_dir / "debug").mkdir(parents=True, exist_ok=True)
    CURRENT_RUN_DIR.set(run_dir)

    async with headed_context(STORAGE_STATE, user_data_dir=PROFILE_DIR) as ctx:
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        print(f"[probe] navigating to {FLOW_URL}")
        await page.goto(FLOW_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)
        await _dump(page, "01-landing")

        # Step 2: enter the workspace (left nav appears here). 새 프로젝트 is the
        # reliable entry; we do NOT touch the agent chat — we head straight for
        # the classic tools nav.
        await _try_click(
            page,
            "new_project",
            [
                lambda p: p.get_by_role("button", name=re.compile(r"새 프로젝트|new project", re.I)),
                lambda p: p.get_by_text(re.compile(r"^\s*새 프로젝트\s*$|^\s*new project\s*$", re.I)),
            ],
        )
        await page.wait_for_timeout(4000)
        await _dump(page, "02-workspace")

        # Step 3: the prompt-bar "add_2 만들기" (+) button — classic "create new
        # media" entry; may open a plain image/video generator menu.
        clicked = await _try_click(
            page,
            "add_create",
            [
                lambda p: p.get_by_role("button", name=re.compile(r"add_2 만들기|^add_2$", re.I)),
            ],
        )
        if clicked:
            await page.wait_for_timeout(2500)
            await _dump(page, "03-add-menu")
            # Dismiss any popover before the next probe.
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)

        # Step 4: the 캐릭터 (Character) section — "Create a character" is plain
        # Imagen generation (no agent chat), and maps directly to our s00 sheets.
        clicked = await _try_click(
            page,
            "character_nav",
            [
                lambda p: p.get_by_role("button", name=re.compile(r"accessibility_new 캐릭터|^캐릭터$|create a character", re.I)),
                lambda p: p.get_by_text(re.compile(r"^\s*캐릭터\s*$|create a character", re.I)),
            ],
        )
        if clicked:
            await page.wait_for_timeout(3000)
            await _dump(page, "04-character")

        print("\n[probe] Inspect the open browser window. The 'candidates.txt' files in")
        print(f"        {run_dir / 'debug'} list every clickable element at each step.")
        print("[probe] Leaving browser open 40s...")
        await page.wait_for_timeout(40000)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
