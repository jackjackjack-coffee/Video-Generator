# Phase B quickstart — selector iteration on Windows

Phase B = teaching the Playwright adapters to drive the **live** Google Flow UI.
It must run on a local machine with a real, visible browser and your Google
login — not in a cloud container. Run it from a **local Claude Code session**
(the `claude` CLI in a terminal, or the Claude Code desktop app / IDE extension)
opened on this repo.

## 0. Prerequisites (one time)
- Python **3.12** (not 3.13). Git. Node 18+.
- Branch: `claude/compassionate-brahmagupta-eKuPB` (PR #2 — the verified code).
- Run `./scripts/windows_setup.ps1` — it installs everything and runs the free
  pre-flight (doctor / dry-run / credits). Stop and fix if any of those fail.

## 1. Log in to Google Flow (one time)
```powershell
python scripts/login_google_flow.py
```
Sign in manually in the window that opens. It snapshots `.auth/` so later runs
reuse the session. Re-run only if you later hit `LoginRequired`.

## 2. First target — the free image stage
```powershell
creativeforge run musinsa-king-choice --only s00_character_sheets
```
- `s00` and `s01` are **Imagen images = free**. Iterate selectors here as much as
  you want at zero credit cost. Only video (`s02`) spends credits.
- Omit `--auto-approve` so you reach the approval gate and can pick the best
  variant with `[v]` before approving.

## 3. The selector-iteration loop
A first-guess selector will usually miss. When it does, the run raises
`SelectorMiss` and writes, under `runs/<id>/debug/`:

| file | what it gives you |
|------|-------------------|
| `<ts>-<label>.png` | full-page screenshot at the moment of the miss |
| `<ts>-<label>.html` | the live DOM |
| `<ts>-<label>.candidates.txt` | **ranked list of visible clickable elements, each with a ready-to-paste Playwright locator** |

`<label>` names the failed action (e.g. `open_image_tool`, `prompt_textbox`,
`generate_button`) — it maps directly to a `first_visible(... label=...)` call in
`creativeforge/browser/flow_imagen.py` (or `flow_veo.py`).

**Fix it:**
1. Open `…candidates.txt`, find the element you wanted, copy its `lambda p: …` line.
2. In `flow_imagen.py` / `flow_veo.py`, find the `first_visible` block with the
   matching `label=`.
3. **Prepend** your lambda to that block's candidate list. Keep the old ones
   below — they're cheap and self-heal across Flow's A/B UI changes. Never delete
   a candidate unless it's verifiably dead.
4. Re-run the same `--only s00_character_sheets`. Repeat per miss.

Both files already `import re`, so `re.compile(...)` in a pasted lambda just works.

## 4. Extra tooling when a selector is stubborn
```powershell
# Record selectors interactively against the logged-in UI:
playwright codegen https://labs.google/fx/tools/flow --load-storage .auth/google.json

# Step through the adapter with the Playwright inspector:
$env:PWDEBUG=1 ;  creativeforge run musinsa-king-choice --only s00_character_sheets
```

## 5. Progression after images work
1. `--only s00_character_sheets` → selectors solid, sheets approved.
2. `--only s01_cut_images` (still free) → uses sheets as references.
3. `--only s02_cut_videos` — **now credits are spent.** Stay draft-first:
   all cuts on `veo-3.1-fast` (~180 cr). Check `creativeforge credits …` first.
   Only flip approved HERO cuts to high-quality afterward (see CLAUDE.md).
4. `--only s03_voice` — edge_tts scratch; switch to Voicebox for the final dub
   (CLAUDE.md → Voice). Listen to cut05 "무진장!" before committing.
5. `--only s04_audio` (needs `PIXABAY_API_KEY`) → `--only s05_compose` (Remotion).

`creativeforge resume <run_id>` picks up from the first unapproved stage if you
stop midway.

## Operating rules
All the judgment calls — Extend vs. fresh, draft-first credits, variant picking,
voice strategy — live in **CLAUDE.md**, which auto-loads at session start. Skim it
before `s02`.
