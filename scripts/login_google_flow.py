"""One-time Google Flow login bootstrap — attaches to YOUR real Chrome.

Why this approach: Google blocks OAuth sign-in from Playwright-*launched*
browsers ("이 브라우저 또는 앱이 안전하지 않을 수 있습니다" / "this browser or app
may not be secure"). The block keys on the browser being launched under
automation, not on cookies. So we don't let Playwright launch the login browser:

  1. We start YOUR real installed Chrome as a normal process, with a dedicated
     profile dir and a remote-debugging port.
  2. You sign in by hand in that 100%-real Chrome window.
  3. Playwright merely *attaches* over the debugging port to snapshot the session
     to .auth/google.json.

Generation runs (flow_imagen/flow_veo) reuse the same profile dir
(.auth/chrome-profile), which now holds your login cookies — Flow loads you as
already signed in, so the OAuth security screen never appears again.

Re-run this whenever the session expires (Flow shows a sign-in button again).

Usage:
    python scripts/login_google_flow.py
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import httpx
from playwright.async_api import async_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
AUTH_DIR = REPO_ROOT / ".auth"
STORAGE_STATE = AUTH_DIR / "google.json"
PROFILE_DIR = AUTH_DIR / "chrome-profile"
FLOW_URL = "https://labs.google/fx/tools/flow"
CDP_PORT = 9222


def _find_chrome() -> str | None:
    """Locate the real Chrome binary. Override with CHROME_PATH if needed."""
    env = os.environ.get("CHROME_PATH")
    if env and Path(env).exists():
        return env
    for name in ("chrome", "google-chrome", "google-chrome-stable", "chrome.exe"):
        found = shutil.which(name)
        if found:
            return found
    candidates = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    ]
    for c in candidates:
        try:
            if c and str(c) and c.exists():
                return str(c)
        except OSError:
            continue
    return None


def _looks_signed_in(storage_state: dict) -> bool:
    """True if the snapshot has Google auth cookies (no page selectors involved).

    Google sets SID/SAPISID/SSID/__Secure-1PSID on .google.com domains once
    signed in. Checking cookies (not the DOM) keeps this robust against Flow's
    shifting UI.
    """
    auth_names = {"SID", "SAPISID", "SSID", "HSID", "__Secure-1PSID", "__Secure-3PSID"}
    for c in (storage_state or {}).get("cookies", []):
        if c.get("name") in auth_names and "google" in (c.get("domain") or ""):
            return True
    return False


async def _wait_for_cdp(timeout_s: float = 30.0) -> bool:
    """Poll the DevTools endpoint until Chrome is ready (or timeout)."""
    deadline = time.time() + timeout_s
    async with httpx.AsyncClient() as client:
        while time.time() < deadline:
            try:
                r = await client.get(f"http://127.0.0.1:{CDP_PORT}/json/version", timeout=1.0)
                if r.status_code == 200:
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.5)
    return False


async def main() -> int:
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    chrome = _find_chrome()
    if not chrome:
        print("[error] Could not find Chrome. Set CHROME_PATH to your chrome.exe and re-run, e.g.:")
        print(r'        $env:CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"')
        return 1

    print(f"Launching your real Chrome:\n  {chrome}")
    print(f"  profile : {PROFILE_DIR}")
    print(f"  port    : {CDP_PORT}")
    print("\n(If Chrome is already running on this profile, close ALL Chrome windows first.)")

    proc = subprocess.Popen(
        [
            chrome,
            f"--user-data-dir={PROFILE_DIR}",
            f"--remote-debugging-port={CDP_PORT}",
            "--no-first-run",
            "--no-default-browser-check",
            FLOW_URL,
        ]
    )

    if not await _wait_for_cdp():
        print(
            "[error] Chrome didn't expose the debugging port within 30s.\n"
            "        Likely another Chrome is already using this profile. Close all\n"
            "        Chrome windows and re-run this script."
        )
        try:
            proc.terminate()
        except Exception:
            pass
        return 1

    print(
        "\nIn the Chrome window that just opened:\n"
        "  1. Sign in with your AI Pro Google account.\n"
        "  2. Click through any consent screens.\n"
        "  3. Confirm Flow's main UI is visible (you should see your avatar).\n"
        "\nThen come back here and press ENTER."
    )
    await asyncio.get_running_loop().run_in_executor(None, input)

    # Attach (do NOT launch) and snapshot the session as a portable fallback.
    signed_in = False
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
            ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
            state = await ctx.storage_state(path=str(STORAGE_STATE))
            signed_in = _looks_signed_in(state)
            print(f"Saved storage_state → {STORAGE_STATE}")
            # Disconnect only; leave the user's Chrome running so they can close it.
    except Exception as e:
        print(f"[warn] could not snapshot storage_state via CDP: {e}")
        print("       The on-disk profile still holds your login, so generation should work anyway.")

    if not signed_in:
        print(
            "\n[warn] Could not confirm a Google sign-in in this profile (no Google auth\n"
            "       cookies found). If Flow still showed a sign-in button, complete the\n"
            "       login and re-run this script before generating."
        )

    print(
        "\nDone. IMPORTANT: close that Chrome window now so the profile is free for generation.\n"
        "Then run:  creativeforge run musinsa-king-choice --only s00_character_sheets"
    )
    return 0 if signed_in else 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
