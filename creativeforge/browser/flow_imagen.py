"""Imagen 4 Ultra automation on labs.google/fx/tools/flow.

The selectors are **first-guess fallback chains**. They will mostly miss on the
first paired-session run; that's expected. The `first_visible` helper dumps the
DOM on miss so we can extend each chain with a working locator. Keep old
candidates at the bottom of each list — they're cheap and they self-heal when
Flow ships UI changes.

UI evolution policy: prepend new selectors, never delete unless verifiably dead.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from typing import TYPE_CHECKING

from playwright.async_api import Page, expect

from creativeforge.browser.selectors import LoginRequired, first_visible

if TYPE_CHECKING:
    from creativeforge.adapters.base import GenRequest, GenResult

FLOW_URL = "https://labs.google/fx/tools/flow"


async def _ensure_logged_in(page: Page) -> None:
    """Heuristic: a sign-in button on the page means we're logged out."""
    try:
        signin = page.get_by_role("button", name=re.compile(r"sign\s*in", re.I)).first
        await signin.wait_for(state="visible", timeout=2000)
        raise LoginRequired()
    except LoginRequired:
        raise
    except Exception:
        return  # no sign-in button visible → assume logged in


async def _maybe_handle_captcha(page: Page) -> None:
    """If a challenge iframe / verify text appears, block on user input."""
    try:
        challenge = page.get_by_text(re.compile(r"verify|i'?m not a robot|challenge", re.I)).first
        await challenge.wait_for(state="visible", timeout=1500)
    except Exception:
        return
    print("\n[captcha] Solve the challenge in the open browser window, then press ENTER here.")
    await asyncio.get_running_loop().run_in_executor(None, input)


async def _open_image_tool(page: Page) -> None:
    btn = await first_visible(
        page,
        [
            lambda p: p.get_by_role("link", name=re.compile(r"image", re.I)),
            lambda p: p.get_by_role("button", name=re.compile(r"image", re.I)),
            lambda p: p.get_by_text(re.compile(r"^image$", re.I)),
        ],
        label="open_image_tool",
    )
    await btn.click()


async def _select_model(page: Page, model: str | None) -> None:
    if not model:
        return
    picker = await first_visible(
        page,
        [
            lambda p: p.get_by_role("button", name=re.compile(r"model", re.I)),
            lambda p: p.locator("button:has-text('Imagen')"),
            lambda p: p.locator("[data-testid*=model]"),
        ],
        label="model_picker_open",
    )
    await picker.click()
    pretty = model.replace("-", " ")  # "imagen-4-ultra" → "imagen 4 ultra"
    option = await first_visible(
        page,
        [
            lambda p: p.get_by_role("option", name=re.compile(pretty, re.I)),
            lambda p: p.get_by_text(re.compile(pretty, re.I)),
        ],
        label="model_option",
    )
    await option.click()


async def _select_aspect_ratio(page: Page, aspect: str) -> None:
    picker = await first_visible(
        page,
        [
            lambda p: p.get_by_role("button", name=re.compile(r"aspect|ratio", re.I)),
            lambda p: p.locator("button:has-text('16:9')"),
            lambda p: p.locator("button:has-text('9:16')"),
            lambda p: p.locator("[data-testid*=aspect]"),
        ],
        label="aspect_picker_open",
    )
    await picker.click()
    option = await first_visible(
        page,
        [
            lambda p: p.get_by_role("option", name=aspect),
            lambda p: p.get_by_text(aspect, exact=True),
        ],
        label=f"aspect_option_{aspect}",
    )
    await option.click()


async def _upload_references(page: Page, references: list[Path]) -> None:
    if not references:
        return
    trigger = await first_visible(
        page,
        [
            lambda p: p.get_by_role("button", name=re.compile(r"add\s+reference|reference\s+image|\+", re.I)),
            lambda p: p.locator("button:has-text('Reference')"),
            lambda p: p.locator("input[type=file]").first,
        ],
        label="reference_upload_trigger",
    )
    # File-input shortcut: if the matched element is the input itself, set files directly.
    tag = await trigger.evaluate("el => el.tagName")
    if tag.lower() == "input":
        await trigger.set_input_files([str(p) for p in references])
        return
    async with page.expect_file_chooser() as fc:
        await trigger.click()
    chooser = await fc.value
    await chooser.set_files([str(p) for p in references])


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
            lambda p: p.get_by_role("button", name=re.compile(r"^generate$|create", re.I)),
            lambda p: p.locator("button:has-text('Generate')"),
        ],
        label="generate_button",
    )
    await btn.click()


async def _wait_for_variants(page: Page, *, expected: int = 4, timeout_ms: int = 600_000) -> None:
    grid_item = await first_visible(
        page,
        [
            lambda p: p.locator("[data-testid*=result]"),
            lambda p: p.locator("img[alt*='generated' i]"),
            lambda p: p.locator("[role=img]"),
        ],
        label="variant_grid",
        timeout_ms=30_000,
    )
    # Once at least one is visible, wait for the full set.
    await expect(grid_item.locator("xpath=..").locator("> *")).to_have_count(expected, timeout=timeout_ms)


async def _download_first_variant(page: Page, dest: Path) -> Path:
    variant = await first_visible(
        page,
        [
            lambda p: p.locator("[data-testid*=result]").first,
            lambda p: p.locator("img[alt*='generated' i]").first,
        ],
        label="variant_thumb",
    )
    await variant.click()
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


async def generate_image(page: Page, req: "GenRequest", out_dir: Path) -> "GenResult":
    from creativeforge.adapters.base import GenResult  # local import: avoids circular load

    item_id = req.extra.get("item_id", "image")
    await page.goto(FLOW_URL, wait_until="domcontentloaded")
    await _ensure_logged_in(page)
    await _maybe_handle_captcha(page)
    await _open_image_tool(page)
    await _select_model(page, req.model)
    await _select_aspect_ratio(page, req.aspect_ratio or "9:16")
    await _upload_references(page, req.references)
    await _fill_prompt(page, req.prompt)
    await _submit(page)
    await _wait_for_variants(page, expected=4)
    dest = out_dir / f"{item_id}.png"
    path = await _download_first_variant(page, dest)
    return GenResult(
        path=path,
        model_used=req.model or "imagen-4-ultra",
        raw_meta={"item_id": item_id, "variant_index": 0, "aspect_ratio": req.aspect_ratio},
    )
