"""Veo 3.1 high-quality automation on labs.google/fx/tools/flow.

Same selector-fallback discipline as flow_imagen.py — first-guess chains that
the paired session will refine. See `flow_imagen.py` header for the policy.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from typing import TYPE_CHECKING

from playwright.async_api import Page

from creativeforge.browser.selectors import LoginRequired, capture_process_shot, first_visible

if TYPE_CHECKING:
    from creativeforge.adapters.base import GenRequest, GenResult

FLOW_URL = "https://labs.google/fx/tools/flow"


async def _ensure_logged_in(page: Page) -> None:
    try:
        signin = page.get_by_role("button", name=re.compile(r"sign\s*in", re.I)).first
        await signin.wait_for(state="visible", timeout=2000)
        raise LoginRequired()
    except LoginRequired:
        raise
    except Exception:
        return


async def _maybe_handle_captcha(page: Page) -> None:
    try:
        challenge = page.get_by_text(re.compile(r"verify|i'?m not a robot|challenge", re.I)).first
        await challenge.wait_for(state="visible", timeout=1500)
    except Exception:
        return
    print("\n[captcha] Solve the challenge in the open browser window, then press ENTER here.")
    await asyncio.get_event_loop().run_in_executor(None, input)


async def _open_video_tool(page: Page) -> None:
    btn = await first_visible(
        page,
        [
            lambda p: p.get_by_role("link", name=re.compile(r"video", re.I)),
            lambda p: p.get_by_role("button", name=re.compile(r"video", re.I)),
            lambda p: p.get_by_text(re.compile(r"^video$", re.I)),
        ],
        label="open_video_tool",
    )
    await btn.click()


async def _select_model(page: Page, model: str | None) -> None:
    if not model:
        return
    picker = await first_visible(
        page,
        [
            lambda p: p.get_by_role("button", name=re.compile(r"model", re.I)),
            lambda p: p.locator("button:has-text('Veo')"),
            lambda p: p.locator("[data-testid*=model]"),
        ],
        label="model_picker_open",
    )
    await picker.click()
    pretty = model.replace("-", " ")
    option = await first_visible(
        page,
        [
            lambda p: p.get_by_role("option", name=re.compile(pretty, re.I)),
            lambda p: p.get_by_text(re.compile(pretty, re.I)),
        ],
        label="model_option",
    )
    await option.click()


async def _select_output_count(page: Page, count: int) -> None:
    """Set how many variants to generate. Each variant costs credits, so the
    pipeline passes the budgeted count. Best-effort — selectors refined in Phase B.
    """
    if count <= 1:
        return  # default is usually 1; nothing to do
    try:
        picker = await first_visible(
            page,
            [
                lambda p: p.get_by_role("button", name=re.compile(r"output|count|number|variations?", re.I)),
                lambda p: p.locator("[data-testid*=count], [data-testid*=output]"),
            ],
            label="output_count_picker",
            timeout_ms=4000,
        )
        await picker.click()
        option = await first_visible(
            page,
            [
                lambda p: p.get_by_role("option", name=re.compile(rf"\b{count}\b")),
                lambda p: p.get_by_text(re.compile(rf"^{count}$")),
            ],
            label=f"output_count_{count}",
            timeout_ms=4000,
        )
        await option.click()
    except Exception:
        print(f"[veo] could not set output count to {count}; using UI default.")


async def _ensure_high_quality(page: Page) -> None:
    """Veo's 'high quality' toggle costs ~3x credits but is required for 1080p.

    Best-effort: if a switch labeled 'high quality' exists and is off, flip it.
    """
    try:
        toggle = page.get_by_role("switch", name=re.compile(r"high\s*quality", re.I)).first
        await toggle.wait_for(state="visible", timeout=2000)
        checked = await toggle.get_attribute("aria-checked")
        if checked != "true":
            await toggle.click()
    except Exception:
        return


async def _upload_start_frame(page: Page, references: list[Path]) -> None:
    """Veo accepts a single start-frame image to preserve identity."""
    if not references:
        print("[veo] no reference image; falling back to text-only (degraded quality).")
        return
    ref = references[0]
    trigger = await first_visible(
        page,
        [
            lambda p: p.get_by_role("button", name=re.compile(r"add\s+image|start\s+frame|reference|\+", re.I)),
            lambda p: p.locator("button:has-text('Image')"),
            lambda p: p.locator("input[type=file]").first,
        ],
        label="start_frame_trigger",
    )
    tag = await trigger.evaluate("el => el.tagName")
    if tag.lower() == "input":
        await trigger.set_input_files([str(ref)])
        return
    async with page.expect_file_chooser() as fc:
        await trigger.click()
    chooser = await fc.value
    await chooser.set_files([str(ref)])


async def _fill_prompt(page: Page, prompt: str) -> None:
    box = await first_visible(
        page,
        [
            lambda p: p.get_by_role("textbox", name=re.compile(r"prompt", re.I)),
            lambda p: p.get_by_placeholder(re.compile(r"prompt|describe", re.I)),
            lambda p: p.locator("textarea").first,
        ],
        label="prompt_textbox",
    )
    await box.fill(prompt)


async def _submit(page: Page) -> None:
    btn = await first_visible(
        page,
        [
            lambda p: p.get_by_role("button", name=re.compile(r"^generate$|create|render", re.I)),
            lambda p: p.locator("button:has-text('Generate')"),
        ],
        label="generate_button",
    )
    await btn.click()


async def _wait_for_render(page: Page, *, timeout_ms: int = 600_000) -> None:
    """Poll until either a 'done'/'completed' indicator appears or credit_exhausted."""
    deadline = asyncio.get_event_loop().time() + timeout_ms / 1000
    while asyncio.get_event_loop().time() < deadline:
        # Credit-exhausted short-circuit.
        try:
            err = page.get_by_text(re.compile(r"credit|quota|limit\s*exhausted|out\s*of", re.I)).first
            await err.wait_for(state="visible", timeout=1000)
            raise RuntimeError(f"credit_exhausted: {await err.text_content()}")
        except RuntimeError:
            raise
        except Exception:
            pass
        # Success indicator.
        try:
            done = page.locator("video, a[download], button[aria-label*='download' i]").first
            await done.wait_for(state="visible", timeout=3000)
            return
        except Exception:
            continue
    raise TimeoutError("Veo render did not complete within timeout")


async def _download_result(page: Page, dest: Path) -> Path:
    dl_btn = await first_visible(
        page,
        [
            lambda p: p.get_by_role("button", name=re.compile(r"download", re.I)),
            lambda p: p.locator("a[download]"),
            lambda p: p.locator("button[aria-label*='download' i]"),
        ],
        label="download_button",
    )
    async with page.expect_download() as dl:
        await dl_btn.click()
    download = await dl.value
    dest.parent.mkdir(parents=True, exist_ok=True)
    await download.save_as(str(dest))
    return dest


async def generate_video(page: Page, req: "GenRequest", out_dir: Path) -> "GenResult":
    from creativeforge.adapters.base import GenResult  # local import: avoids circular load

    item_id = req.extra.get("item_id", "video")
    await page.goto(FLOW_URL, wait_until="domcontentloaded")
    await _ensure_logged_in(page)
    await _maybe_handle_captcha(page)
    variants = int(req.extra.get("variants", 1))
    await _open_video_tool(page)
    await _select_model(page, req.model)
    await _ensure_high_quality(page)
    await _select_output_count(page, variants)
    await capture_process_shot(page, out_dir, item_id, "1-ui-ready")
    await _upload_start_frame(page, req.references)
    await _fill_prompt(page, req.prompt)
    await capture_process_shot(page, out_dir, item_id, "2-prompt-entered")
    await _submit(page)
    await _wait_for_render(page)
    await capture_process_shot(page, out_dir, item_id, "3-generated")
    dest = out_dir / f"{item_id}.mp4"
    path = await _download_result(page, dest)
    return GenResult(
        path=path,
        model_used=req.model or "veo-3.1-high-quality",
        raw_meta={
            "item_id": item_id,
            "had_reference": bool(req.references),
            "variants": variants,
            "duration_s": req.extra.get("duration_s"),
        },
    )
