# START HERE — Phase B launch (Windows)

This repo is **creativeforge**, the AI video pipeline for the Musinsa 무진장
광고제 2026 entry "왕의 선택". You're on the verified branch
`claude/compassionate-brahmagupta-eKuPB` (PR #2). All cloud-side code is done and
tested; the remaining work is **Phase B** — iterating Playwright selectors
against the live Google Flow UI, which must run here on Windows.

Two reading orders:
- **Just want to start?** Do the commands below, then launch `claude` and paste
  the first message at the bottom.
- **Want the full loop / judgment calls?** Read `PHASE_B_QUICKSTART.md` and
  `CLAUDE.md` (CLAUDE.md auto-loads when you launch `claude`).

---

## Prerequisites (install these yourself first — the setup script does NOT)

| Tool | Install | Needed for |
|------|---------|-----------|
| **Python 3.12** (not 3.13) | `winget install -e --id Python.Python.3.12` | everything. **pip is bundled** — no separate install. |
| **Git** | `winget install -e --id Git.Git` | cloning the repo |
| **Node.js LTS** | `winget install -e --id OpenJS.NodeJS.LTS` | only the FINAL render stage (`s05_compose`, Remotion). NOT needed for Phase B selector work, but install now to avoid a surprise later. Playwright itself does not need system Node. |
| Claude CLI | (you already have it) | running the local agent |

`windows_setup.ps1` installs the rest for you: the `creativeforge` Python package
and the Playwright Chromium browser.

## Logins — what's automatic vs. manual

- The browser **opens itself.** Both the login script and every `creativeforge run`
  launch a visible Chromium automatically. You never open Flow by hand.
- You sign in **once**, manually, during `python scripts/login_google_flow.py`.
  It saves the session to `.auth/chrome-profile/`; later runs come up already
  logged in. Re-run that script only if Flow shows a sign-in button again.
- This is a **dedicated Chromium profile — NOT your everyday Chrome** and not the
  Claude Chrome extension. Sign in inside the window that pops up.
- **Gemini login is NOT required.** All generation goes through Google Flow only;
  "gemini" in the code is just a credit-accounting label.

---

## Commands (PowerShell)

### One time: install base tools, then OPEN A NEW TERMINAL
> Use Python 3.12, not 3.13 — some deps lack 3.13 wheels. Skip any tool you
> already have (`python --version`, `git --version`, `node --version`). The PATH
> only updates in a *fresh* terminal, so close this one and open a new PowerShell
> after these finish.
```powershell
winget install -e --id Python.Python.3.12
winget install -e --id Git.Git
winget install -e --id OpenJS.NodeJS.LTS
```

### In the new terminal: set up and launch (copy-paste the whole block)
```powershell
python --version                                   # expect Python 3.12.x
git clone https://github.com/jackjackjack-coffee/Video-Generator.git
cd Video-Generator
git checkout claude/compassionate-brahmagupta-eKuPB
powershell -ExecutionPolicy Bypass -File .\scripts\windows_setup.ps1   # installs pkg + Chromium, runs free pre-flight
python scripts/login_google_flow.py                # one-time Google sign-in (window opens; log in manually)
claude                                             # launches the local agent — paste the message below
```

Notes:
- You already have the Claude CLI, so there's no install step for it.
- `windows_setup.ps1` **checks** for Python 3.12 but does **not** install it — that's the `winget` step above.
- s04_audio later needs a Pixabay key: `setx PIXABAY_API_KEY "your-key"` (then reopen the terminal). Not needed for the first stages.

---

## First message to paste into `claude`

```
Read HANDOFF.md, CLAUDE.md, and PHASE_B_QUICKSTART.md first. We're doing Phase B:
iterating Playwright selectors against the live Google Flow UI on Windows.

I've already run scripts/windows_setup.ps1 and python scripts/login_google_flow.py.
Start by running:
  creativeforge run musinsa-king-choice --only s00_character_sheets

When a selector misses, it raises SelectorMiss and writes
runs/<id>/debug/<ts>-<label>.{html,png,candidates.txt}. Open the newest
*.candidates.txt, find the element matching the failed <label>, and PREPEND its
suggested locator lambda to the matching first_visible(... label=...) block in
creativeforge/browser/flow_imagen.py (keep the old candidates below it). Re-run
the same command and repeat per miss.

Stay draft-first on credits: s00 and s01 are FREE image stages — get selectors
solid there before touching s02 video. Do NOT run s02 without telling me the
credit estimate first.
```

## Who does what

- **The agent** runs `creativeforge`, reads the `candidates.txt` dump on a selector
  miss, and edits `flow_imagen.py` / `flow_veo.py` to prepend the right locator,
  then re-runs. You do **not** edit Python yourself.
- **You** handle only the human parts: the one-time Google sign-in; solving a
  CAPTCHA if Flow shows one (the run pauses for it, then you press ENTER); the
  approval gate (`a` approve / `v` pick best variant / `r` regenerate / `s` skip /
  `q` quit); and answering the agent if it asks which on-screen element it should
  target.
