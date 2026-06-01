# musinsa-king-choice — DECISIONS

타임스탬프 + 근거 포함 의사결정 누적 기록. 새 결정은 위로 추가(reverse chronological).

---

## 2026-05-31 — Flow 이미지 도구 UI 탐색 + 오디오 파이프라인 재설계

### Flow 이미지 생성 UI 진입 경로 (탐색 결과, UNVERIFIED)
- 직전 로컬 세션에서 알아낸 흐름(세션 리셋으로 유실 → 코드/문서에 박제): `새 프로젝트` →
  에이전트 패널 닫기(`닫기`) → **`에이전트` 필 클릭**(프롬프트 바가 직접 이미지 생성 모드로
  전환, 모델 기본값 Imagen 4) → 결합형 설정 버튼 `Imagen 4 crop_16_9 x2`(모델 Imagen 4/Nano
  Banana, 종횡비 `crop_16_9`/`crop_9_16`, 개수 `x2`) → `만들기`/arrow_forward 제출 →
  타일은 `모든 미디어`에 생성.
- **결정**: 9:16 = `crop_9_16` 토큰. 기존 코드가 `"9:16"` 문자열을 그대로 넘겨 빗나갔음 →
  `flow_imagen.py`에 `_ASPECT_TOKENS` 매핑 추가. radix id(`radix-:r3s:` 등)는 렌더마다
  바뀌므로 **절대 id로 셀렉트하지 않고 텍스트로 매칭**.
- 발견한 후보들을 `flow_imagen.py` 각 체인의 **최상단**에 `UNVERIFIED` 주석과 함께 선반영.
  로컬 로그인 세션에서 `python scripts/probe_image_tool.py`(읽기 전용)로 확정.

### 오디오 파이프라인 재설계 (Veo 네이티브 + 전용 TTS 하이브리드)
- **음성(대사)**: 전용 TTS 유지(Veo로 옮기지 않음). 근거 — 대사가 6개 컷에 걸친 짧은 사극
  한국어라 캐릭터별 음색 일관성·정확한 대본·무료 재생성이 중요. Veo는 컷마다 음색이 흔들리고
  HQ 클립 재생성은 ~3배 크레딧. 단종/수양 **음성 2개로 분리**(단종=`ko-KR-HyunsuMultilingualNeural`,
  수양=`ko-KR-InJoonNeural`). storyboard `voice:` 필드만 수정 — 어댑터 코드 변경 불필요.
  ⚠️ 클라우드 환경은 edge-tts 엔드포인트(speech.platform.bing.com) SSL 프록시로 차단 → 음성
  이름·음색은 로컬에서 `edge-tts --list-voices`로 확정. Hyunsu 계열 없으면 둘 다 InJoon로 폴백.
- **효과음(SFX)**: Pixabay SFX 검색 경로 **제거**. 현장 효과음/앰비언스는 Veo 네이티브
  오디오(컷 클립에 포함, compose에서 대사 밑으로 덕킹). 유일한 비현장 효과음(타이틀 카드 "쿵"
  임팩트)은 Remotion에 **번들 에셋** `remotion/public/sfx-bundled/impact.mp3`로 커밋.
- **음악**: Pixabay(자동 API) + YouTube Audio Library(API 없음 → `remotion/public/music-manual/`
  수동 드롭인). 두 음원 모두 도구 정책 + 상업 이용 OK. storyboard `music:` 블록에서 파일명·
  타이밍·볼륨 지정(전통 베드 0–20s, 패션 비트 20–28s).
- **믹싱**: Remotion이 컷 네이티브 오디오(덕킹) + TTS 음성(주) + 음악 베드(대사 구간 덕킹) +
  타이틀 임팩트를 합성. 볼륨은 storyboard `audio:` 블록 → 매니페스트 `AUDIO_MIX`. 최종 레벨은
  로컬에서 귀로 확정.
- **edge-tts 상업 라이선스 주의**: edge-tts는 비공식 MS 엔드포인트라 상업 이용 보장이 없음.
  광고제(상업) 최종 제출 전 Clova/ElevenLabs(유료, 상업 라이선스)로 교체 검토 —
  `project.yaml`의 `fallback_adapter: clova` 훅 이미 존재.

## 2026-05-27 — Flow Playwright 어댑터 Phase A 스캐폴딩 (페어드 세션 준비)

- `creativeforge/browser/selectors.py`: `first_visible()` fallback 체인 + 미스 시 HTML/스크린샷 덤프. `CURRENT_RUN_DIR` ContextVar로 덤프 위치 주입.
- `creativeforge/browser/flow_imagen.py` / `flow_veo.py`: Imagen·Veo Playwright 자동화 (네비 → 모델·종횡비 픽 → 참조 업로드 → 프롬프트 → 제출 → 대기 → 다운로드). 셀렉터는 1차 추측이므로 실제 UI에서 거의 다 빗나갈 것 — 의도된 출발점.
- 어댑터 파일은 `headed_context` 열고 `Page`를 헬퍼에 넘기는 얇은 래퍼로 축소.
- `Pipeline._get_adapter`가 Flow 어댑터에만 `browser_cfg` + `project_dir` 주입. 다른 어댑터는 영향 없음.
- `scripts/login_google_flow.py`: 최초 로그인 부트스트랩. `.auth/chrome-profile/`(주) + `.auth/google.json`(보조) 둘 다 저장.
- **결정**: storage_state 단독은 Google anti-bot에 약함 → `user_data_dir`(영구 Chrome 프로필) 우선, storage_state는 fallback. `headed_context`가 이미 그렇게 동작.
- **결정**: 4개 Imagen variant 중 첫 번째만 반환. 4개 전체 반환은 `GenResult`를 list 타입으로 확장해야 해서 보류 — 승인 게이트의 `[r]` 키로 재생성 처리.
- **결정**: 캡차는 절대 우회 시도 안 함. 감지하면 `input()`으로 블록해서 사용자가 수동 해결.
- 다음 세션은 Windows 로컬 Claude Code에서 진행. 사용자가 클론 + venv + `playwright install chromium` + 로그인 스크립트 실행 → 셀렉터 페어드 이터레이션.

## 2026-05-26 — pipeline.py / ui/approve.py 1차 구현 + edge_tts pitch 버그 픽스

- `creativeforge/pipeline.py`: topological stage ordering, adapter dispatch by kind, state.json 매 아이템마다 저장, `--only/--from` 플래그 지원.
- `creativeforge/ui/approve.py`: 아이템 단위 `[a/r/e/i/s/q]` 게이트. `[e]` 누르면 `runs/<id>/prompt-overrides/<id>.yaml` 열어서 prompt 재정의 (pipeline이 이 파일을 자동으로 읽음).
- 어댑터 인스턴스화는 `_dispatch` 시점 지연 — `--dry-run`에 PIXABAY_API_KEY 등 시크릿이 필요 없도록.
- 레퍼런스 해석: `"Sheet 3 (Suyang)"` 같은 라벨을 `sheet3*.png` 정규식으로 best-effort 매칭. 미스 시 경고 후 빈 references로 진행.
- `edge_tts.py` pitch 값: `%` → `Hz`로 변경 (edge-tts는 `±NHz` 형식만 허용). 기존 `-10%` 등은 호출 시 에러.

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
