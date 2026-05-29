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
from typing import Callable

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


async def capture_process_shot(page: Page, out_dir: Path, item_id: str, step: str) -> None:
    """Save a process-documentation screenshot to runs/<id>/process-doc/<stage>/.

    Called at key moments during generation so the user has evidence of AI tool
    usage for contest submission. Best-effort: never raises.
    """
    run_dir = CURRENT_RUN_DIR.get()
    if run_dir is None:
        return
    dest = run_dir / "process-doc" / out_dir.name / f"{item_id}-{step}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        await page.screenshot(path=str(dest))
    except Exception:
        pass


# Selectors we can't guess are found fastest by eyeballing the page's actual
# interactive elements. On a miss we dump this inventory next to the HTML/PNG so
# the iterator gets a ready-made menu of locators instead of grepping raw DOM.
_CANDIDATE_JS = r"""
() => {
  const sel = 'button,[role=button],a[href],input,textarea,select,'
    + '[role=textbox],[role=combobox],[role=option],[contenteditable],[data-testid]';
  const out = [];
  for (const el of document.querySelectorAll(sel)) {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0 || el.offsetParent === null) continue;
    const text = (el.innerText || el.value || '').trim().replace(/\s+/g, ' ').slice(0, 60);
    out.push({
      tag: el.tagName.toLowerCase(),
      role: el.getAttribute('role') || '',
      ariaLabel: el.getAttribute('aria-label') || '',
      text: text,
      testid: el.getAttribute('data-testid') || '',
      id: el.id || '',
      placeholder: el.getAttribute('placeholder') || '',
      type: el.getAttribute('type') || '',
    });
    if (out.length >= 200) break;
  }
  return out;
}
"""


def _suggest_locator(c: dict) -> str:
    """A copy-pasteable first-guess Playwright locator for one element."""
    name = (c.get("ariaLabel") or c.get("text") or "").replace('"', "").replace("\\", "")
    if c.get("testid"):
        return f"lambda p: p.locator(\"[data-testid='{c['testid']}']\")"
    if c.get("id"):
        return f"lambda p: p.locator(\"#{c['id']}\")"
    if name and c.get("role"):
        return f'lambda p: p.get_by_role("{c["role"]}", name=re.compile(r"{name}", re.I))'
    if name and c["tag"] in ("button", "a"):
        role = "link" if c["tag"] == "a" else "button"
        return f'lambda p: p.get_by_role("{role}", name=re.compile(r"{name}", re.I))'
    if c.get("placeholder"):
        ph = c["placeholder"].replace('"', "")
        return f'lambda p: p.get_by_placeholder(re.compile(r"{ph}", re.I))'
    if name:
        return f'lambda p: p.get_by_text(re.compile(r"{name}", re.I))'
    return f"lambda p: p.locator(\"{c['tag']}\")  # weak — add text/role"


def _format_candidates(cands: list[dict]) -> str:
    lines = [
        "# Visible interactive elements at the selector miss.",
        "# Pick the one you want, then PREPEND its locator to the candidate list for",
        "# this action in flow_imagen.py / flow_veo.py (those files already import re).",
        "",
    ]
    for i, c in enumerate(cands):
        label = c.get("ariaLabel") or c.get("text") or c.get("placeholder") or "(no text)"
        attrs = " ".join(f"{k}={c[k]!r}" for k in ("role", "testid", "id", "type") if c.get(k))
        lines.append(f"[{i:02d}] <{c['tag']}> {label!r}  {attrs}".rstrip())
        lines.append(f"     {_suggest_locator(c)}")
    return "\n".join(lines) + "\n"


async def dump_debug(page: Page, label: str) -> Path | None:
    """Write `<run_dir>/debug/<ts>-<label>.{html,png,candidates.txt}`. Best-effort."""
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
    # Element inventory — the fastest way to find the right selector on a miss.
    try:
        cands = await page.evaluate(_CANDIDATE_JS)
        (base / f"{ts}-{safe}.candidates.txt").write_text(
            _format_candidates(cands), encoding="utf-8"
        )
    except Exception:
        pass
    return html_path
