#!/usr/bin/env python3
"""Migrate Musinsa-ad-festival repo → projects/musinsa-king-choice/.

Usage:
    python scripts/import_musinsa.py /path/to/Musinsa-ad-festival

Produces:
    projects/musinsa-king-choice/
    ├── project.yaml
    ├── CONTEXT.md            (initial draft, hand-edit before relying on it)
    ├── DECISIONS.md          (timestamped decision log)
    ├── prompts/00..04.yaml
    ├── storyboard.yaml
    ├── branding/             (copied from public/branding + public/musinsa-logo.png)
    ├── references/           (copied if existing character sheets present)
    └── remotion/             (src/ + package.json copied; KingsChoice.tsx points to generated manifest)
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

from ruamel.yaml import YAML

yaml = YAML()
yaml.default_flow_style = False
yaml.preserve_quotes = True
yaml.width = 200
yaml.allow_unicode = True


# ── Helpers ───────────────────────────────────────────────────────────────────

def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _write_yaml(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f)


# ── Parsers ───────────────────────────────────────────────────────────────────

def parse_character_sheets(md_text: str) -> dict:
    """Parse prompts/00-character-sheets.md → structured yaml. Extracts first fenced
    code block under each `## SHEET N — title` as the prompt body."""
    items: dict[str, dict] = {}
    header_re = re.compile(
        r"^##\s+(?:SHEET|Sheet)\s+(\d+)\s*[—\-:]?\s*([^\n]+)$",
        flags=re.MULTILINE,
    )
    matches = list(header_re.finditer(md_text))
    for i, m in enumerate(matches):
        num = m.group(1).strip()
        title = m.group(2).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        body = md_text[body_start:body_end]
        fence = re.search(r"```[^\n]*\n(.*?)```", body, flags=re.DOTALL)
        prompt = fence.group(1).strip() if fence else body.strip()
        items[_sheet_id(num, title)] = {"title": title, "prompt": prompt}
    return {
        "defaults": {
            "aspect_ratio": "9:16",
            "style_keywords": "Joseon dynasty Korean palace, cinematic lighting, photorealistic, ultra-detailed",
        },
        "items": items,
        "raw_source": "prompts/00-character-sheets.md (Musinsa-ad-festival)",
    }


def _sheet_id(num: str, title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9가-힣]+", "-", title.lower()).strip("-")[:40]
    return f"sheet{num}-{slug}" if slug else f"sheet{num}"


def parse_cut_prompts_md(md_text: str, kind: str) -> dict:
    """Parse 01-imagen-prompts.md or 02-veo3-prompts.md into per-cut items.

    Headers look like `## CUT 01 — 수양대군 등장 (0~3s)`. References are on a line
    starting with `🎯 **Reference**:` and the actual prompt body is the first fenced
    code block after the header.
    """
    items: dict[str, dict] = {}
    # Split on `## CUT NN — title ...` headers (case-insensitive on CUT/Cut/컷).
    header_re = re.compile(
        r"^##\s+(?:CUT|Cut|컷)\s+(\d+)\s*[—\-:]?\s*([^\n]+)$",
        flags=re.MULTILINE,
    )
    matches = list(header_re.finditer(md_text))
    if not matches:
        return {"raw": md_text, "_note": f"could not parse {kind}; left raw"}

    for i, m in enumerate(matches):
        num = m.group(1)
        title_line = m.group(2).strip()
        # strip trailing "(0~3s)" or "(0-3s)" timing parens from title
        title = re.sub(r"\s*\([^)]*\)\s*$", "", title_line).strip()

        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        body = md_text[body_start:body_end]

        # Extract reference line.
        refs_match = re.search(
            r"^[^\n]*?(?:Reference|레퍼런스|참조)[^\n]*?:\s*([^\n]+)$",
            body,
            flags=re.MULTILINE | re.IGNORECASE,
        )
        ref_list: list[str] = []
        if refs_match:
            raw_refs = refs_match.group(1)
            # Strip markdown bold markers and trailing notes.
            raw_refs = re.sub(r"\*+", "", raw_refs).strip()
            ref_list = [r.strip() for r in re.split(r"\s*[+,،、·•]\s*", raw_refs) if r.strip()]

        # Extract first fenced code block as the prompt body.
        fence = re.search(r"```[^\n]*\n(.*?)```", body, flags=re.DOTALL)
        prompt = fence.group(1).strip() if fence else body.strip()

        cut_id = f"cut{int(num):02d}"
        items[cut_id] = {
            "label": title,
            "references": ref_list,
            "prompt": prompt,
        }

    return {
        "defaults": {"aspect_ratio": "9:16"},
        "items": items,
        "raw_source": f"prompts/{'01' if kind == 'image' else '02'}-*.md (Musinsa-ad-festival)",
    }


def parse_pixabay_keywords(md_text: str) -> dict:
    """Extract BGM/SFX search keywords."""
    bgm: list[str] = []
    sfx: list[str] = []
    current = None
    for line in md_text.splitlines():
        if re.search(r"^\s*##.*BGM", line, flags=re.IGNORECASE):
            current = bgm
        elif re.search(r"^\s*##.*SFX|효과음", line, flags=re.IGNORECASE):
            current = sfx
        elif current is not None:
            m = re.match(r"^\s*[-*]\s+(.+)$", line)
            if m:
                current.append(m.group(1).strip())
    return {
        "music_queries": bgm,
        "sfx_queries": sfx,
        "raw_source": "prompts/03-pixabay-keywords.md (Musinsa-ad-festival)",
    }


def parse_constants_ts(ts_text: str) -> dict:
    """Pull CUTS and SUBTITLES arrays out of src/constants.ts via regex."""
    cuts: list[dict] = []
    cut_block = re.search(r"export const CUTS\s*=\s*\[(.+?)\]\s*as const", ts_text, flags=re.DOTALL)
    if cut_block:
        for line in cut_block.group(1).splitlines():
            m = re.search(
                r'\{\s*id:\s*"(?P<id>[^"]+)"\s*,\s*start:\s*(?P<start>\d+)\s*,\s*duration:\s*(?P<dur>\d+)\s*,\s*label:\s*"(?P<label>[^"]+)"',
                line,
            )
            if m:
                cuts.append(
                    {
                        "id": m["id"],
                        "start_s": int(m["start"]),
                        "duration_s": int(m["dur"]),
                        "label": m["label"],
                    }
                )

    subs: list[dict] = []
    sub_block = re.search(r"export const SUBTITLES[^=]*=\s*\[(.+?)\];", ts_text, flags=re.DOTALL)
    if sub_block:
        for m in re.finditer(
            r'\{\s*start:\s*(\d+)\s*,\s*end:\s*(\d+)\s*,\s*text:\s*"((?:[^"\\]|\\.)*)"',
            sub_block.group(1),
        ):
            raw = m.group(3)
            text = (
                raw.replace("\\n", "\n")
                .replace("\\t", "\t")
                .replace('\\"', '"')
                .replace("\\\\", "\\")
            )
            subs.append(
                {"start_s": int(m.group(1)), "end_s": int(m.group(2)), "text": text}
            )

    # Merge subtitles into cuts as `dialogue` when timings line up.
    for cut in cuts:
        for s in subs:
            if s["start_s"] == cut["start_s"]:
                cut["dialogue"] = {
                    "speaker": _guess_speaker(cut["label"], s["text"]),
                    "voice": "ko-KR-InJoonNeural",
                    "style": _guess_style(cut["label"], s["text"]),
                    "text": s["text"],
                }
                break

    return {
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "cuts": cuts,
        "title_card": {"start_s": 28, "duration_s": 2, "text": "왕의 선택"},
        "subtitles_legacy": subs,
    }


def _guess_speaker(label: str, text: str) -> str:
    if "수양" in label or "수양" in text:
        return "suyang"
    if "단종" in label or "단종" in text or "전하" in text:
        return "danjong"
    return "narrator"


def _guess_style(label: str, text: str) -> str:
    if "무진장" in text and ("슬프" in text or "절규" in label):
        return "tearful"
    if "수양" in label or "위협" in label:
        return "stern"
    if "충격" in label or "송구" in text:
        return "comic"
    return "royal"


# ── Outputs ───────────────────────────────────────────────────────────────────

PROJECT_YAML_TEMPLATE = {
    "project": {
        "id": "musinsa-king-choice",
        "title": "왕의 선택",
        "description": "무신사 무진장 광고제 2026 출품작 — 계유정난을 재해석한 30초 광고.",
        "output": {"width": 1080, "height": 1920, "fps": 30, "duration_s": 30},
    },
    "stages": {
        "s00_character_sheets": {
            "adapter": "google_flow_imagen",
            "model": "imagen-4-ultra",
            "aspect_ratio": "9:16",
            "prompts_file": "prompts/00-character-sheets.yaml",
        },
        "s01_cut_images": {
            "adapter": "google_flow_imagen",
            "model": "imagen-4-ultra",
            "aspect_ratio": "9:16",
            "prompts_file": "prompts/01-cut-images.yaml",
            "depends_on": ["s00_character_sheets"],
        },
        "s02_cut_videos": {
            "adapter": "google_flow_veo",
            "model": "veo-3.1-high-quality",
            "prompts_file": "prompts/02-cut-videos.yaml",
            "depends_on": ["s01_cut_images"],
        },
        "s03_voice": {
            "adapter": "edge_tts",
            "voice": "ko-KR-InJoonNeural",
            "fallback_adapter": "clova",
            "enabled": True,
        },
        "s04_audio": {
            "adapter": "pixabay",
            "keywords_file": "prompts/04-audio-keywords.yaml",
        },
        "s05_compose": {
            "adapter": "remotion",
            "project_remotion_dir": "remotion",
            "composition_id": "KingsChoice",
            "output_filename": "final.mp4",
        },
    },
    "approval": {"mode": "gate", "preview": "open"},
    "browser": {
        "headed": True,
        "storage_state": "../../.auth/google.json",
        "user_data_dir": "../../.auth/chrome-profile",
    },
    "storyboard_file": "storyboard.yaml",
}


CONTEXT_MD_TEMPLATE = """# musinsa-king-choice — CONTEXT

> **읽는 사람이 처음이라고 가정하고** 작성됨. 새 Claude 세션·새 사용자가 첫 줄에 읽으세요.
> 자동 생성된 초안입니다. 사람이 한 번 손보고 갱신하세요.

## 프로젝트 한 줄

무신사 무진장 광고제 2026 출품작 "**왕의 선택**" — 계유정난(1453)을 재해석한 30초 세로형(9:16) AI 영상 광고.

## 마감

| 일자 | 작업 |
|---|---|
| 2026-06-05 23:59 | 예선 마감 (SNS 업로드 + 무신사 앱 접수) |
| 2026-06-30 | SNS 게시물 유지 마감 |

## 현재 진행도 (마이그레이션 직후 스냅샷)

| 스테이지 | 상태 | 비고 |
|---|---|---|
| s00 character sheets | **재생성 필요** | 1차 생성 시 의상·머리 오류 발견. 보강 프롬프트는 `prompts/00-character-sheets.yaml`에 반영. `references/`에 기존 시트(있다면) 보관됨. |
| s01 cut images | 대기 | s00 승인 후. 컷별 프롬프트 `prompts/01-cut-images.yaml`. |
| s02 cut videos | 대기 | Veo 3.1 high quality. 컷별 8초 이하. |
| s03 voice | 대기 | Edge TTS 기본 (`ko-KR-InJoonNeural`). 대사는 `storyboard.yaml`의 각 컷 `dialogue` 필드. |
| s04 audio | 대기 | Pixabay BGM 2곡 (사극 톤 0~20s, 경쾌 20~30s) + SFX 3 (sword/comic/impact). 키워드 `prompts/04-audio-keywords.yaml`. |
| s05 compose | 대기 | Remotion. `remotion/src/generated/manifest.ts`는 `storyboard.yaml`에서 자동 생성. |

## 알려진 이슈 / 우회법

- **Veo 8초 한계**: 각 컷 duration_s ≤ 8 을 storyboard.yaml에서 강제. cut03(4s), cut04(4s) 등 안전 범위.
- **Imagen 4 한국 얼굴 일관성**: 캐릭터 시트를 매번 reference로 넘기지 않으면 얼굴이 흔들림. s01 어댑터가 `depends_on: s00`을 보고 자동 reference 주입.
- **단종 머리(전모/익선관)**: 직접 명시해도 자주 무시됨. 시트 프롬프트에 명확한 영문 묘사(`black silk wing-shaped royal cap (ikseongwan)`) 포함됨. 그래도 안 되면 사용자가 [e]dit-prompt로 패치.
- **Google Flow 자동화**: 어댑터는 STUB 상태. Playwright 셀렉터 작업은 다음 세션에서 라이브 UI 보며 작성. 그동안은 수동 진행 가능 — 산출물을 `runs/<id>/stage-NN/`에 직접 떨어뜨리면 다음 스테이지가 인식.

## 브랜드·법적 제약 (변경 금지)

- 무신사 무진장 공식 KV는 `branding/`에 있음. 영상 내 **최소 1회** 노출 필수 (현재 28~30s 타이틀 카드).
- AI 제작 과정 캡처본을 모든 단계에서 저장 (`runs/<id>/`에 meta.json + attempts 보존됨 → 제출 시 활용).
- 사용 가능 도구만: Google AI Pro (Imagen/Veo), Pixabay, YouTube Audio Library, Remotion(개인 무료), Edge TTS / Naver Clova / ElevenLabs (유료 OK). **Runway 무료, Suno/Udio 무료 금지** (비상업 약관).
- 캐릭터·역사 사건: 공공 도메인 (단종·수양대군·계유정난).

## 다음 액션 1-3개

1. **Google Flow Playwright 어댑터 작성** (s00, s01, s02). 라이브 UI 보면서 selector 카탈로그 만들고 다운로드 흐름 검증.
2. **사용자**: 캐릭터 시트 재생성 (어댑터 작성 전까지 수동도 가능). 결과를 `references/`에 배치.
3. **음성 dry run**: `creativeforge run musinsa-king-choice --dry-run` 으로 s03 Edge TTS 단독 테스트 (`--only s03_voice`).

## 핵심 파일

- `project.yaml` — 어댑터·모델 선언. 음성을 끄려면 `s03_voice.enabled: false`.
- `storyboard.yaml` — 컷 타이밍·대사·title card. **여기만 고치면 자막·manifest 다 자동 반영**.
- `prompts/*.yaml` — 컷별 프롬프트. [e]dit-prompt로 런타임 수정 시 `runs/<id>/prompt-overrides/`에 격리 저장.
- `remotion/src/Composition.tsx` — `generated/manifest.ts`를 import. 수정 거의 불필요.

## 원본 레포

`https://github.com/jackjackjack-coffee/Musinsa-ad-festival` — 광고제 출품 완료 후 GitHub Archive 예정. 마이그레이션 시점까지의 prompts·Remotion 코드 원본 보존용.
"""


DECISIONS_MD_TEMPLATE = """# musinsa-king-choice — DECISIONS

타임스탬프 + 근거 포함 의사결정 누적 기록. 새 결정은 위로 추가(reverse chronological).

---

## 2026-05-26 — Video-Generator 레포로 분리, creativeforge 코어 + projects/ 구조 채택

- **결정**: `Musinsa-ad-festival` 단독 레포 → `Video-Generator` 레포 안 `creativeforge` 코어 + `projects/musinsa-king-choice/` 첫 입주자.
- **근거**: 두 번째 광고제를 또 처음부터 만들기 싫음. Playwright + 어댑터 + 승인 게이트는 재사용 가능한 코어, 프롬프트·스토리보드·Remotion은 프로젝트별.
- **음성 정책**: 항상 enabled (사용자가 명시적으로 끄지 않는 한). MVP는 Edge TTS, 품질 부족 시 Clova/ElevenLabs로 어댑터 교체.
- **기존 레포 처리**: 광고제 출품 완료 시점에 GitHub Archive. 그때까지 보존.

## 2026-05-25 — 베이지 톤 KV 채택

- 사극 톤매너와 색 조화. `branding/key-color-reference.jpg`가 기준.

## 2026-05-24 — 단종 모던 룩 단독 컷 제외

- 시간 부족 + 캐릭터 일관성 ↓. 컷6 변신 시퀀스에 통합.

## 2026-05-22 — 시나리오 "왕의 선택" 채택

- 사극 + "선택" 모티프, 음식 의존 ↓, 단종/수양 대비로 임팩트 ↑.

## 도구 정책 (변경 금지)

- 편집: Remotion (개인 무료 + 상업이용 OK)
- 영상 생성: Google Flow Veo 3.1 high quality (AI Pro 유료 → 상업이용 OK)
- 이미지: Google Flow Imagen 4 Ultra
- 음악: Pixabay / YouTube Audio Library
- **금지**: Runway 무료, Suno/Udio 무료 (비상업 약관)
"""


def write_remotion_skeleton(dest: Path, musinsa_src: Path) -> None:
    """Copy src/*.tsx into remotion/src/ and rewrite KingsChoice.tsx to import the
    generated manifest instead of the hand-written constants.ts."""
    rm_src = dest / "remotion" / "src"
    rm_src.mkdir(parents=True, exist_ok=True)

    # Copy components.
    for name in ("Subtitle.tsx", "TitleCard.tsx", "index.ts"):
        s = musinsa_src / "src" / name
        if s.exists():
            shutil.copy2(s, rm_src / name)

    # KingsChoice: rewrite constants import to generated manifest.
    src_text = (musinsa_src / "src" / "KingsChoice.tsx").read_text()
    src_text = src_text.replace('from "./constants"', 'from "./generated/manifest"')
    (rm_src / "KingsChoice.tsx").write_text(src_text)

    # Stub manifest (will be regenerated by adapter; this is just a placeholder).
    (rm_src / "generated").mkdir(parents=True, exist_ok=True)
    (rm_src / "generated" / "manifest.ts").write_text(
        "// placeholder — regenerated by creativeforge.adapters.compose.remotion\n"
        "export const FPS = 30;\n"
        "export const WIDTH = 1080;\n"
        "export const HEIGHT = 1920;\n"
        "export const TOTAL_SECONDS = 30;\n"
        "export const TOTAL_FRAMES = TOTAL_SECONDS * FPS;\n"
        "export const TITLE_CARD_FRAMES = 2 * FPS;\n"
        "export const AVAILABLE_CLIPS: ReadonlySet<string> = new Set<string>();\n"
        "export const CUTS = [] as const;\n"
        "export const SUBTITLES: { start: number; end: number; text: string }[] = [];\n"
    )

    # Copy package.json + tsconfig from musinsa repo.
    for name in ("package.json", "tsconfig.json"):
        s = musinsa_src / name
        if s.exists():
            shutil.copy2(s, dest / "remotion" / name)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    musinsa = Path(sys.argv[1]).resolve()
    if not (musinsa / "PLAN.md").exists():
        print(f"Not a Musinsa-ad-festival repo: {musinsa}")
        sys.exit(1)

    dest = Path(__file__).parent.parent / "projects" / "musinsa-king-choice"
    dest.mkdir(parents=True, exist_ok=True)

    # 1. project.yaml
    _write_yaml(dest / "project.yaml", PROJECT_YAML_TEMPLATE)

    # 2. prompts/*.yaml
    p = musinsa / "prompts"
    if (p / "00-character-sheets.md").exists():
        _write_yaml(dest / "prompts" / "00-character-sheets.yaml",
                    parse_character_sheets(_read(p / "00-character-sheets.md")))
    if (p / "01-imagen-prompts.md").exists():
        _write_yaml(dest / "prompts" / "01-cut-images.yaml",
                    parse_cut_prompts_md(_read(p / "01-imagen-prompts.md"), "image"))
    if (p / "02-veo3-prompts.md").exists():
        _write_yaml(dest / "prompts" / "02-cut-videos.yaml",
                    parse_cut_prompts_md(_read(p / "02-veo3-prompts.md"), "video"))
    if (p / "03-pixabay-keywords.md").exists():
        _write_yaml(dest / "prompts" / "04-audio-keywords.yaml",
                    parse_pixabay_keywords(_read(p / "03-pixabay-keywords.md")))

    # 3. storyboard.yaml from constants.ts
    constants = musinsa / "src" / "constants.ts"
    if constants.exists():
        _write_yaml(dest / "storyboard.yaml", parse_constants_ts(_read(constants)))

    # 4. CONTEXT.md + DECISIONS.md
    (dest / "CONTEXT.md").write_text(CONTEXT_MD_TEMPLATE, encoding="utf-8")
    (dest / "DECISIONS.md").write_text(DECISIONS_MD_TEMPLATE, encoding="utf-8")

    # 5. branding/
    branding_dest = dest / "branding"
    branding_dest.mkdir(exist_ok=True)
    src_branding = musinsa / "public" / "branding"
    if src_branding.exists():
        for f in src_branding.iterdir():
            shutil.copy2(f, branding_dest / f.name)
    logo = musinsa / "public" / "musinsa-logo.png"
    if logo.exists():
        shutil.copy2(logo, branding_dest / "musinsa-logo.png")

    # 6. references/
    refs_dest = dest / "references"
    refs_dest.mkdir(exist_ok=True)
    src_refs = musinsa / "public" / "references"
    if src_refs.exists():
        for f in src_refs.iterdir():
            shutil.copy2(f, refs_dest / f.name)
    if not any(refs_dest.iterdir()):
        (refs_dest / ".keep").write_text("# Place character sheets here after s00 stage runs.\n")

    # 7. remotion/
    write_remotion_skeleton(dest, musinsa)

    print(f"✓ Migrated → {dest}")
    print("  Inspect CONTEXT.md and DECISIONS.md, then commit.")


if __name__ == "__main__":
    main()
