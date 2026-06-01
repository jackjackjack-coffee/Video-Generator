"""Read-only probe of Google Flow's DIRECT image-generation UI.

Captured finding (2026-05-31 paired session, then lost to a session reset — this
script reconstructs it so it's never lost again):

    새 프로젝트 (new project)
      → close the agent chat panel (닫기 / close)
      → click the '에이전트' pill  ← switches the prompt bar into DIRECT image mode
      → a combined config button appears reading e.g. "Imagen 4 crop_16_9 x2"
         (radix id like radix-:r3s: — non-deterministic, never select by id)
         exposing model (Imagen 4 / Nano Banana), aspect (crop_16_9 / crop_9_16),
         and count (x2)
      → 만들기 / arrow_forward submits; tiles land in 모든 미디어 (all media)

This project needs 9:16 → the 'crop_9_16' token.

The probe NEVER fills a prompt and NEVER submits. It just navigates and dumps a
clickable-element map (+ HTML/screenshot) at each step so the selectors in
`creativeforge/browser/flow_imagen.py` (currently marked UNVERIFIED) can be confirmed.
It is only meaningful on a machine that is logged into Flow (run the login bootstrap
first): `python scripts/login_google_flow.py`.

Usage:
    python scripts/probe_image_tool.py
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from creativeforge.browser.selectors import CURRENT_RUN_DIR, dump_debug
from creativeforge.browser.session import headed_context

REPO_ROOT = Path(__file__).resolve().parent.parent
AUTH_DIR = REPO_ROOT / ".auth"
STORAGE_STATE = AUTH_DIR / "google.json"
PROFILE_DIR = AUTH_DIR / "chrome-profile"
FLOW_URL = "https://labs.google/fx/tools/flow"

# Enumerate the clickable / interactive elements with enough attributes to write a
# working Playwright locator from the output.
_ELEMENTS_JS = r"""
() => {
  const sel = 'button,[role=button],a,[role=link],[role=option],[role=menuitem],'
            + '[role=menuitemradio],[role=tab],[role=radio],[role=combobox],textarea,input';
  const out = [];
  for (const el of document.querySelectorAll(sel)) {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) continue;
    const text = (el.innerText || el.value || el.getAttribute('aria-label') || '')
      .trim().replace(/\s+/g, ' ').slice(0, 60);
    out.push({
      tag: el.tagName.toLowerCase(),
      role: el.getAttribute('role'),
      text: text,
      aria: el.getAttribute('aria-label'),
      id: el.id || null,
      testid: el.getAttribute('data-testid'),
      x: Math.round(r.left),
      y: Math.round(r.top),
    });
  }
  return out;
}
"""


async def _dump_elements(page, run_dir: Path, label: str) -> None:
    """Print + persist a clickable-element map, plus HTML/screenshot via dump_debug."""
    try:
        elements = await page.evaluate(_ELEMENTS_JS)
    except Exception as e:  # pragma: no cover - probe is best-effort
        print(f"[probe] element dump failed @ {label}: {e}")
        elements = []
    print(f"\n===== elements @ {label} ({len(elements)}) =====")
    for i, el in enumerate(elements):
        meta = " ".join(
            f"{k}={el[k]}" for k in ("role", "id", "testid") if el.get(k)
        )
        print(f"  [{i:02d}] {el['tag']:<8} ({el['x']},{el['y']})  {el['text']!r}  {meta}")
    print("=" * 40)
    (run_dir / f"elements-{label}.json").write_text(
        json.dumps(elements, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    await dump_debug(page, label)


async def _try_click(page, label: str, candidates) -> bool:
    """Click the first visible candidate; report and continue on miss (read-only safe)."""
    for factory in candidates:
        try:
            loc = factory(page).first
            await loc.wait_for(state="visible", timeout=3000)
            await loc.click()
            print(f"[probe] clicked: {label}")
            return True
        except Exception:
            continue
    print(f"[probe] MISS: {label} (see the element dump to extend flow_imagen.py)")
    return False


async def _pause(prompt: str) -> None:
    print(f"\n>>> {prompt}")
    await asyncio.get_event_loop().run_in_executor(None, input)


async def main() -> int:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = REPO_ROOT / "runs" / "_probe" / ts
    run_dir.mkdir(parents=True, exist_ok=True)
    CURRENT_RUN_DIR.set(run_dir)  # so dump_debug writes under runs/_probe/<ts>/debug/
    print(f"[probe] dumps → {run_dir}")

    async with headed_context(storage_state=STORAGE_STATE, user_data_dir=PROFILE_DIR) as ctx:
        page = await ctx.new_page()
        await page.goto(FLOW_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)
        await _dump_elements(page, run_dir, "00-loaded")

        await _try_click(
            page, "new_project",
            [lambda p: p.get_by_role("button", name=re.compile(r"새\s*프로젝트|new\s+project", re.I))],
        )
        await page.wait_for_timeout(3000)
        await _dump_elements(page, run_dir, "10-new-project")

        await _try_click(
            page, "close_agent",
            [lambda p: p.get_by_role("button", name=re.compile(r"닫기|close", re.I))],
        )
        await page.wait_for_timeout(1500)
        await _dump_elements(page, run_dir, "20-agent-closed")

        # The key step: the '에이전트' pill switches the prompt bar into direct image mode.
        await _try_click(
            page, "agent_pill",
            [
                lambda p: p.get_by_role("button", name=re.compile(r"에이전트", re.I)),
                lambda p: p.get_by_text(re.compile(r"^\s*에이전트\s*$")),
            ],
        )
        await page.wait_for_timeout(1500)
        await _dump_elements(page, run_dir, "30-direct-mode")

        # Open the combined config button ("Imagen 4 crop_16_9 x2") and map model/aspect/count.
        opened = await _try_click(
            page, "config_button",
            [lambda p: p.get_by_role("button", name=re.compile(r"imagen\s*4|nano\s*banana|crop_(16_9|9_16)", re.I))],
        )
        if opened:
            await page.wait_for_timeout(1200)
            await _dump_elements(page, run_dir, "40-config-open")

        await _pause(
            "Inspect the open config popover. Look for the 9:16 control (token 'crop_9_16').\n"
            "    Press ENTER to dump final state and exit. (This probe never submits.)"
        )
        await _dump_elements(page, run_dir, "99-final")

    print(f"\n[probe] done. Paste the relevant elements-*.json entries to confirm the")
    print("[probe] UNVERIFIED candidates in creativeforge/browser/flow_imagen.py.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
