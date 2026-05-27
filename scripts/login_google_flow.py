"""One-time Google Flow login bootstrap.

Opens a headed Chromium pointed at labs.google/fx/tools/flow, waits for the
user to sign in manually, then snapshots both `.auth/chrome-profile/` (via
persistent context) and `.auth/google.json` (storage_state).

Re-run this script whenever the session expires (Flow shows a sign-in button
instead of your avatar).

Usage:
    python scripts/login_google_flow.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from creativeforge.browser.session import headed_context

REPO_ROOT = Path(__file__).resolve().parent.parent
AUTH_DIR = REPO_ROOT / ".auth"
STORAGE_STATE = AUTH_DIR / "google.json"
PROFILE_DIR = AUTH_DIR / "chrome-profile"
FLOW_URL = "https://labs.google/fx/tools/flow"


async def main() -> int:
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Opening {FLOW_URL} in a fresh Chromium window…")
    print(f"  profile dir : {PROFILE_DIR}")
    print(f"  storage path: {STORAGE_STATE}")

    async with headed_context(
        storage_state=STORAGE_STATE,
        user_data_dir=PROFILE_DIR,
    ) as ctx:
        page = await ctx.new_page()
        await page.goto(FLOW_URL, wait_until="domcontentloaded")

        print(
            "\nIn the browser window:\n"
            "  1. Sign in with your AI Pro Google account.\n"
            "  2. Click through any consent screens.\n"
            "  3. Confirm Flow's main UI is visible (you should see your avatar).\n"
            "\nThen come back here and press ENTER."
        )
        await asyncio.get_event_loop().run_in_executor(None, input)

        # Snapshot storage_state alongside the persistent profile so it's usable
        # from machines that don't share the chrome-profile dir.
        try:
            await ctx.storage_state(path=str(STORAGE_STATE))
            print(f"Saved storage_state → {STORAGE_STATE}")
        except Exception as e:
            print(f"[warn] could not save storage_state: {e}")

    print("Done. The persistent profile is in .auth/chrome-profile/.")
    print("You can now run: creativeforge run musinsa-king-choice --only s00_character_sheets")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
