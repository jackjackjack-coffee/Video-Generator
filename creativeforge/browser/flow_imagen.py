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

from playwright.async_api import Page

from creativeforge.browser.selectors import LoginRequired, capture_process_shot, first_visible

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
    await asyncio.get_event_loop().run_in_executor(None, input)


async def _open_image_tool(page: Page) -> None:
    btn = await first_visible(
        page,
        [
            # 2026 Flow hub: no standalone "Image" button — open a new project, which
            # lands on the canvas (prompt bar + image/video tool + model picker).
            # Locale-independent: bilingual text alternation, falls back to the add_2 icon.
            lambda p: p.get_by_role("button", name=re.compile(r"새 프로젝트|new project", re.I)),
            # Populated landing (promo banner + project grid): "새 프로젝트" renders as
            # a clickable grid TILE (div), not a button — match by text regardless of tag.
            lambda p: p.get_by_text(re.compile(r"^\s*새 프로젝트\s*$|^\s*new project\s*$", re.I)).first,
            lambda p: p.locator("button:has(i.google-symbols:text-is('add_2'))"),
            lambda p: p.get_by_role("button", name=re.compile(r"add_2", re.I)),
            # Older / English-only Flow layouts.
            lambda p: p.get_by_role("link", name=re.compile(r"image", re.I)),
            lambda p: p.get_by_role("button", name=re.compile(r"image", re.I)),
            lambda p: p.get_by_text(re.compile(r"^image$", re.I)),
        ],
        label="open_image_tool",
    )
    await btn.click()


# 2026 agentic Flow: aspect + output-count are radix "tab" groups whose random
# prefix (radix-:r3d:) changes per render, but the trigger *suffix* is stable and
# semantic. The IMAGE section renders before the VIDEO section in the DOM, so for
# values that appear in both groups we take .first (image).
_ASPECT_ICON = {
    "9:16": "crop_9_16",
    "16:9": "crop_16_9",
    "1:1": "crop_square",
    "4:3": "crop_landscape",
    "3:4": "crop_portrait",
}
_ASPECT_TRIGGER = {
    "9:16": "PORTRAIT",
    "16:9": "LANDSCAPE",
    "1:1": "SQUARE",
    "4:3": "LANDSCAPE_4_3",
    "3:4": "PORTRAIT_3_4",
}
# Output-count tab labels: 1 → "1x", 2 → "x2", 3 → "x3", 4 → "x4".
_COUNT_LABEL = {1: "1x", 2: "x2", 3: "x3", 4: "x4"}


async def _open_agent_settings(page: Page) -> None:
    """Open the prompt-bar 'tune 설정' gear → 에이전트 설정 panel."""
    gear = await first_visible(
        page,
        [
            lambda p: p.get_by_role("button", name=re.compile(r"tune\s*설정|tune", re.I)),
            # Older canvas layouts.
            lambda p: p.get_by_role("button", name=re.compile(r"model|settings", re.I)),
            lambda p: p.locator("[data-testid*=settings]"),
        ],
        label="settings_open",
    )
    await gear.click()


async def _set_confirm_before_generating(page: Page, always: bool) -> None:
    """Pick the '생성하기 전에 확인' radio. For free image gen we use '안 함' (auto)
    so the agent renders without an extra confirm step; the pipeline's own
    approval gate is the real control point. (Revisit for video — flow_veo.)

    Best-effort: a missing toggle (UI variant) is not fatal.
    """
    want = r"항상|always" if always else r"안\s*함|off|auto"
    try:
        radio = await first_visible(
            page,
            [lambda p: p.get_by_role("radio", name=re.compile(want, re.I))],
            label="confirm_before_generating",
            timeout_ms=4000,
        )
        await radio.click()
    except Exception as e:
        print(f"[imagen] confirm-before-generating toggle not set ({e}); continuing")


async def _set_image_aspect(page: Page, aspect: str) -> None:
    icon = _ASPECT_ICON.get(aspect, "crop_9_16")
    trigger = _ASPECT_TRIGGER.get(aspect, "PORTRAIT")
    tab = await first_visible(
        page,
        [
            # Image section is first in DOM → .first picks it over the video group.
            lambda p: p.get_by_role("tab", name=re.compile(rf"{icon}\s*{re.escape(aspect)}", re.I)).first,
            lambda p: p.locator(f"[id$='-trigger-{trigger}']").first,
            lambda p: p.get_by_role("tab", name=re.compile(re.escape(aspect), re.I)).first,
        ],
        label=f"image_aspect_{aspect}",
    )
    await tab.click()


async def _set_image_count(page: Page, count: int) -> None:
    label = _COUNT_LABEL.get(count, "x4")
    tab = await first_visible(
        page,
        [
            lambda p: p.get_by_role("tab", name=re.compile(rf"^{re.escape(label)}$", re.I)).first,
            lambda p: p.locator(f"[id$='-trigger-{count}']").first,
        ],
        label=f"image_count_{count}",
    )
    await tab.click()


async def _select_model(page: Page, model: str | None) -> None:
    """Open the image-model dropdown and pick `model` (e.g. 'imagen-4' → 'Imagen 4')."""
    if not model:
        return
    # The dropdown trigger shows the currently-selected model; the image dropdown
    # precedes the video one (Omni Flash) in the DOM, so take .first on the
    # generic arrow_drop_down fallback.
    trigger = await first_visible(
        page,
        [
            lambda p: p.get_by_role("button", name=re.compile(r"nano banana|imagen", re.I)).first,
            lambda p: p.get_by_role("button", name=re.compile(r"arrow_drop_down", re.I)).first,
            # Older canvas layouts.
            lambda p: p.locator("button:has-text('Imagen')"),
            lambda p: p.locator("[data-testid*=model]"),
        ],
        label="model_picker_open",
    )
    await trigger.click()
    pretty = model.replace("-", " ")  # "imagen-4" → "imagen 4"
    option = await first_visible(
        page,
        [
            lambda p: p.get_by_role("option", name=re.compile(pretty, re.I)),
            lambda p: p.get_by_role("menuitem", name=re.compile(pretty, re.I)),
            lambda p: p.get_by_text(re.compile(rf"^{pretty}$", re.I)),
            lambda p: p.get_by_text(re.compile(pretty, re.I)),
        ],
        label="model_option",
    )
    await option.click()


async def _save_settings(page: Page) -> None:
    btn = await first_visible(
        page,
        [
            lambda p: p.get_by_role("button", name=re.compile(r"^저장$|^save$", re.I)),
            lambda p: p.get_by_text(re.compile(r"^저장$|^save$", re.I)),
        ],
        label="settings_save",
    )
    await btn.click()


async def _configure_agent_settings(
    page: Page, model: str | None, aspect: str, count: int = 4
) -> None:
    """Drive the unified 에이전트 설정 panel: confirm-mode → aspect → count →
    image model → 저장. Replaces the old separate model/aspect pickers."""
    await _open_agent_settings(page)
    await _set_confirm_before_generating(page, always=False)
    await _set_image_aspect(page, aspect)
    await _set_image_count(page, count)
    await _select_model(page, model)
    await _save_settings(page)


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
            # 2026 agentic prompt bar: a contenteditable <div role=textbox>. When
            # empty it has NO accessible name (the "무엇을 만들고 싶으신가요?" text is
            # a placeholder span, not an a11y name), so match the contenteditable
            # directly — and FIRST, so we never fall through to the top-left global
            # search <input> (which is also role=textbox and earlier in the DOM).
            lambda p: p.locator("div[contenteditable='true']").first,
            lambda p: p.locator("[contenteditable='true']").first,
            lambda p: p.get_by_role("textbox", name=re.compile(r"무엇을 만들|what.*create|prompt", re.I)),
            # Older canvas layouts.
            lambda p: p.get_by_placeholder(re.compile(r"prompt|describe", re.I)),
            lambda p: p.locator("textarea").first,
        ],
        label="prompt_textbox",
    )
    await box.click()
    try:
        await box.fill(prompt)
    except Exception:
        # contenteditable divs sometimes reject fill(); type into the focused node.
        await box.type(prompt)


async def _submit(page: Page) -> None:
    btn = await first_visible(
        page,
        [
            # Agentic submit is the "arrow_forward 만들기" send button. Match the
            # icon ligature so we don't grab the "add_2 만들기" media-type button.
            lambda p: p.get_by_role("button", name=re.compile(r"arrow_forward", re.I)),
            lambda p: p.get_by_role("button", name=re.compile(r"^만들기$|^send$|^create$", re.I)),
            # Older canvas layouts.
            lambda p: p.get_by_role("button", name=re.compile(r"^generate$|create", re.I)),
            lambda p: p.locator("button:has-text('Generate')"),
        ],
        label="generate_button",
    )
    await btn.click()


async def _wait_for_variants(page: Page, *, expected: int = 4, timeout_ms: int = 600_000) -> None:
    """Wait for generated images to arrive inline in the agentic chat thread.

    Unlike the old fixed 4-up grid, results stream into the conversation, so we
    wait for the FIRST result to appear (generation can take minutes), then let
    the remaining variants settle rather than hard-requiring an exact count.
    """
    # 1) Block until at least one generated image is visible (long timeout —
    #    Imagen renders can take a while).
    await first_visible(
        page,
        [
            lambda p: p.locator("[data-testid*=result] img"),
            lambda p: p.locator("img[alt*='generated' i]"),
            lambda p: p.locator("img[src*='blob']"),
            lambda p: _variant_thumbs(p).first,
        ],
        label="variant_grid",
        timeout_ms=timeout_ms,
    )
    # 2) Let the rest of the set finish rendering, then stop when the count holds
    #    steady across two polls (or the settle window elapses).
    prev = -1
    for _ in range(20):
        await page.wait_for_timeout(2000)
        try:
            now = await _variant_thumbs(page).count()
        except Exception:
            break
        if now >= expected or (now == prev and now > 0):
            break
        prev = now


def _variant_thumbs(p: Page):
    """Locator for the rendered variant thumbnails. First-guess fallback chain;
    Phase B refines against a real results dump on first miss."""
    return p.locator("[data-testid*=result] img, img[alt*='generated' i], img[src*='blob']")


async def _download_one(page: Page, dest: Path) -> Path:
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


async def _download_all_variants(
    page: Page, out_dir: Path, item_id: str, ext: str = ".png"
) -> tuple[Path, list[Path]]:
    """Download every rendered variant to `<item>-v{i}{ext}` and copy v0 to the
    canonical `<item>{ext}`. Returns (canonical_path, [variant paths]).

    Selectors are first-guess (Phase B refines them). On any miss, falls back to
    downloading whatever single variant is reachable.
    """
    import shutil

    out_dir.mkdir(parents=True, exist_ok=True)
    variants: list[Path] = []
    try:
        thumbs = _variant_thumbs(page)
        count = await thumbs.count()
    except Exception:
        count = 0

    if count <= 0:
        # Fallback: grab whatever single variant is visible.
        single = await first_visible(
            page,
            [
                lambda p: _variant_thumbs(p).first,
                lambda p: p.locator("img[alt*='generated' i]").first,
            ],
            label="variant_thumb",
        )
        await single.click()
        variants.append(await _download_one(page, out_dir / f"{item_id}-v0{ext}"))
    else:
        for i in range(count):
            try:
                await thumbs.nth(i).click()
                variants.append(await _download_one(page, out_dir / f"{item_id}-v{i}{ext}"))
            except Exception as e:
                print(f"[imagen] variant {i} download failed: {e}")

    if not variants:
        raise RuntimeError("no variants downloaded")
    canonical = out_dir / f"{item_id}{ext}"
    shutil.copyfile(variants[0], canonical)
    return canonical, variants


async def generate_image(page: Page, req: "GenRequest", out_dir: Path) -> "GenResult":
    from creativeforge.adapters.base import GenResult  # local import: avoids circular load

    item_id = req.extra.get("item_id", "image")
    await page.goto(FLOW_URL, wait_until="domcontentloaded")
    await _ensure_logged_in(page)
    await _maybe_handle_captcha(page)
    await _open_image_tool(page)
    # New agentic session needs a beat to settle before the prompt bar / tune gear
    # are interactive (fixes the first-item 'tune' timing race seen in Phase B).
    await page.wait_for_timeout(2500)
    await _configure_agent_settings(page, req.model, req.aspect_ratio or "9:16", count=4)
    await capture_process_shot(page, out_dir, item_id, "1-ui-ready")
    await _upload_references(page, req.references)
    await _fill_prompt(page, req.prompt)
    await capture_process_shot(page, out_dir, item_id, "2-prompt-entered")
    await _submit(page)
    await _wait_for_variants(page, expected=4)
    await capture_process_shot(page, out_dir, item_id, "3-generated")
    canonical, variants = await _download_all_variants(page, out_dir, item_id, ".png")
    return GenResult(
        path=canonical,
        variant_paths=variants,
        model_used=req.model or "imagen-4",
        raw_meta={
            "item_id": item_id,
            "variant_count": len(variants),
            "aspect_ratio": req.aspect_ratio,
        },
    )
