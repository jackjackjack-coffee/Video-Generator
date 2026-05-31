"""One-off probe: enumerate Flow's available IMAGE models.

Phase B needs to settle the s00 image-model decision. The 2026 agentic Flow UI
defaults the image model to "Nano Banana 2"; the project's standing tool policy
says Imagen 4 Ultra. We can't decide on paper — we have to open the live model
dropdown and read the actual menu.

This reuses the logged-in persistent Chrome profile (.auth/chrome-profile), opens
a new project, opens the "tune 설정" settings panel, clicks the image-model
dropdown, and prints every option it finds. Read-only: it never submits a prompt
and never spends credits.

Usage:
    python scripts/probe_image_models.py
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

from creativeforge.browser.selectors import CURRENT_RUN_DIR, first_visible  # noqa: E402
from creativeforge.browser.session import headed_context  # noqa: E402

PROFILE_DIR = REPO_ROOT / ".auth" / "chrome-profile"
STORAGE_STATE = REPO_ROOT / ".auth" / "google.json"
FLOW_URL = "https://labs.google/fx/tools/flow"

# Collect option-like nodes after the dropdown opens. Radix dropdowns render as
# role=option / role=menuitem inside a popper; grab their visible text.
_OPTIONS_JS = r"""
() => {
  const sel = '[role=option],[role=menuitem],[role=menuitemradio],li[data-radix-collection-item]';
  const out = [];
  for (const el of document.querySelectorAll(sel)) {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) continue;
    const text = (el.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 80);
    if (text) out.push(text);
  }
  return out;
}
"""


async def main() -> int:
    run_dir = REPO_ROOT / "runs" / f"probe-image-models-{datetime.now():%Y%m%d-%H%M%S}"
    (run_dir / "debug").mkdir(parents=True, exist_ok=True)
    CURRENT_RUN_DIR.set(run_dir)

    async with headed_context(STORAGE_STATE, user_data_dir=PROFILE_DIR) as ctx:
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        print(f"[probe] navigating to {FLOW_URL}")
        await page.goto(FLOW_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # 1) New project → agentic session.
        new_project = await first_visible(
            page,
            [
                lambda p: p.get_by_role("button", name=re.compile(r"새 프로젝트|new project", re.I)),
                lambda p: p.locator("button:has(i.google-symbols:text-is('add_2'))"),
            ],
            label="probe_new_project",
        )
        await new_project.click()
        await page.wait_for_timeout(4000)

        # 2) Open the "tune 설정" settings panel.
        tune = await first_visible(
            page,
            [lambda p: p.get_by_role("button", name=re.compile(r"tune", re.I))],
            label="probe_tune",
        )
        await tune.click()
        await page.wait_for_timeout(2000)

        # 3) Click the image-model dropdown. The current default text is
        #    "🍌 Nano Banana 2"; match the dropdown by that, else the first
        #    arrow_drop_down trigger in the panel (image section precedes video).
        dropdown = await first_visible(
            page,
            [
                lambda p: p.get_by_role("button", name=re.compile(r"nano banana", re.I)),
                lambda p: p.get_by_role("button", name=re.compile(r"imagen", re.I)),
                lambda p: p.get_by_role("button", name=re.compile(r"arrow_drop_down", re.I)).first,
            ],
            label="probe_image_model_dropdown",
        )
        await dropdown.click()
        await page.wait_for_timeout(1500)

        options = await page.evaluate(_OPTIONS_JS)
        shot = run_dir / "debug" / "image-model-dropdown-open.png"
        try:
            await page.screenshot(path=str(shot), full_page=True)
        except Exception:
            pass

        print("\n================ IMAGE MODEL OPTIONS ================")
        if options:
            for i, o in enumerate(options):
                print(f"  [{i:02d}] {o}")
        else:
            print("  (no role=option/menuitem nodes found — see screenshot + candidates dump)")
            # Fall back to the generic inventory dump for manual inspection.
            from creativeforge.browser.selectors import dump_debug

            await dump_debug(page, "probe_image_model_options")
        print("====================================================")
        print(f"\n[probe] screenshot: {shot}")
        print("[probe] leaving browser open 20s for manual inspection...")
        await page.wait_for_timeout(20000)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
