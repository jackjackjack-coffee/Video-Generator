# musinsa-king-choice — CONTEXT

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
