# musinsa-king-choice — DECISIONS

타임스탬프 + 근거 포함 의사결정 누적 기록. 새 결정은 위로 추가(reverse chronological).

---

## 2026-05-26 — storyboard cut04/cut09 화자·대사 정정

- cut04 화자: `suyang` → `danjong` (대사 "숙부, 어찌하여…"는 단종이 수양을 부르는 말).
- cut04 대사: `어이하여` → `어찌하여` (정정).
- cut04 스타일: `stern` → `tearful`.
- cut09 화자: `narrator` → `danjong` (단종이 신하들에게 선포).
- 마이그레이션 스크립트의 휴리스틱이 라벨에 "수양"이 포함된 컷을 우선적으로 suyang으로 태깅한 결과였음. 향후 휴리스틱 개선 시 텍스트 내용("숙부"는 단종이 부르는 호칭) 우선 반영.

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
