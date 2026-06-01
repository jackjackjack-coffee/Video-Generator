# START HERE — running the musinsa-king-choice video pipeline

You drive this project from a **Claude Code CLI on your own computer**. Open a terminal and run:

```
cd C:\Users\brown\Video-Generator          # your local project folder
claude --permission-mode acceptEdits         # launches Claude Code on your machine
```

Then **paste one of the prompts below** into Claude, depending on what you want to do.
(`--permission-mode acceptEdits` lets Claude make file edits — e.g. Flow selector fixes —
without stopping to ask each time.)

> Note: the Claude on your machine runs things and opens the browser. A *cloud* Claude
> session (claude.ai/code) edits code and pushes to GitHub but can't see your machine —
> that's why each prompt below starts by pulling the latest code.

---

## A) Generate everything from scratch
Paste this:

> Read HANDOFF.md first. Check out branch `claude/dazzling-meitner-ADVYY` and `git pull`.
> Then run `creativeforge run musinsa-king-choice` to generate from the character sheets
> onward. When Flow needs sign-in or the image step misses its selectors, run
> `scripts/login_google_flow.py` / `scripts/probe_image_tool.py`, fix the selectors in
> `creativeforge/browser/flow_imagen.py`, and continue.

## B) I already made the 5 character sheets by hand
First save them to `projects/musinsa-king-choice/references/`, named exactly:

| File | Character |
|------|-----------|
| `sheet1.png` | King Danjong — royal robe |
| `sheet2.png` | King Danjong — modern fashion |
| `sheet3.png` | Prince Suyang |
| `sheet4.png` | Throne hall |
| `sheet5.png` | Palace exterior + KV flags |

Then paste this:

> Read HANDOFF.md first. Check out branch `claude/dazzling-meitner-ADVYY` and `git pull`.
> My 5 hand-made character sheets are in `projects/musinsa-king-choice/references/`
> (`sheet1.png`…`sheet5.png`). Run `creativeforge run musinsa-king-choice --from s01_cut_images`.
> Handle Flow sign-in/selectors as needed (`scripts/login_google_flow.py`,
> `scripts/probe_image_tool.py`, `creativeforge/browser/flow_imagen.py`) and continue.

## If a run gets interrupted
Paste this:

> Resume the latest musinsa-king-choice run with `creativeforge resume <run_id>` — the run_id
> is printed when a run starts and is the folder name under `runs/`. It continues from the first
> unfinished stage and skips work already done.

---

## What's where (quick map)
- `creativeforge/` — the pipeline tool (provides the `creativeforge` command)
- `projects/musinsa-king-choice/` — this video's `storyboard.yaml`, `prompts/`, `branding/`, `remotion/`
- `projects/musinsa-king-choice/references/` — drop hand-made **sheets / cut images** here (`sheet1.png`, `cut03.png`, …)
- `projects/musinsa-king-choice/remotion/public/clips-manual/` — drop hand-made **cut videos** here (`cut01.mp4` …)
- `projects/musinsa-king-choice/remotion/public/sfx-bundled/impact.mp3` — drop the **쿵** impact sound here
- `scripts/probe_image_tool.py` — confirm Flow's UI selectors (read-only; no generation)
- `HANDOFF.md` — full status + how-to (the source of truth)

**Keep instructions consistent:** this file and `HANDOFF.md` are the canonical entry point —
every session (yours, local, or cloud) should read them so guidance doesn't drift between sessions.
