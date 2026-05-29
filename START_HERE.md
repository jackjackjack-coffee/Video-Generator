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

## Commands (PowerShell)

### One time: install Python 3.12, then OPEN A NEW TERMINAL
> Use 3.12, not 3.13 — some deps lack 3.13 wheels. Skip if `python --version`
> already prints `3.12.x`. The PATH only updates in a *fresh* terminal, so close
> this one and open a new PowerShell after it finishes.
```powershell
winget install -e --id Python.Python.3.12
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

That's it. The agent drives `creativeforge`; you watch the browser window it
opens and approve/pick variants at the gate.
