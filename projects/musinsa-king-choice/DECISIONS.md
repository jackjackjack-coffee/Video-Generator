# musinsa-king-choice — DECISIONS

타임스탬프 + 근거 포함 의사결정 누적 기록. 새 결정은 위로 추가(reverse chronological).

---

## 2026-05-31 — 이미지 모델 결정: Imagen 4 (Imagen 4 Ultra 단종 확인)

- **프로브**: `scripts/probe_image_models.py`로 라이브 Flow 이미지 모델 드롭다운(에이전트 설정 패널)을 열어 실제 가용 목록 확인. 결과 **딱 3종**: `🍌 Nano Banana Pro`, `🍌 Nano Banana 2`(현재 기본값), `Imagen 4`. **`Imagen 4 Ultra`는 드롭다운에서 사라짐** — 프로젝트 기준 모델이 더 이상 존재하지 않음. (스크린샷: `runs/probe-image-models-20260531-183318/debug/image-model-dropdown-open.png`)
- **결정 — 이미지 모델 = `Imagen 4`**: 원래 의도(Imagen 4 Ultra의 포토리얼 룩)에 가장 가까운 잔존 Imagen 티어 유지. `project.yaml` s00/s01의 `model: imagen-4-ultra` → `imagen-4`로 변경. "도구 정책(변경 금지)" 이미지 항목도 갱신(사용자 승인 완료).
  - 검토한 대안: Nano Banana Pro(캐릭터 일관성·한글 텍스트 렌더링 우위 — sheet5 KV 깃발에 유리)와 Nano Banana 2(기본값·저비용). 사용자가 Imagen 4 선택.
  - 상업이용: 3종 모두 동일 유료 AI Pro Flow 제품 경유 → 권리는 모델이 아니라 플랜에서 파생. 최종 출품 전 Google 현행 약관 재확인 필요.
- **크레딧 — 이미지는 무료(확인됨)**: 에이전트 설정의 "생성하기 전에 확인 → 안 함" 툴팁(*"미디어를 생성하고 크레딧을 자동으로 사용합니다"*)은 **동영상 자동 모드**에 적용되는 설명이며 이미지 생성과는 무관. 사용자가 Pro 플랜에서 이미지를 다수 생성한 경험상 이미지 생성은 크레딧을 소비하지 않음 → CLAUDE.md "images are free" 전제 유지. (크레딧 소비는 동영상 모델에 한함.)
- **다음 단계(미구현)**: `flow_imagen.py` 어댑터 재작업 — `_select_model`이 tune 기어만 누르고 끝나서 model_option 미스 발생. 새 흐름은 (1) tune 기어 → 패널 (2) **이미지 모델 드롭다운 트리거 클릭**(드롭다운 열기) (3) `Imagen 4` 옵션 클릭 (4) 종횡비 9:16 탭 + 출력 개수 탭 + `저장`. 프로브 스크립트의 셀렉터(`nano banana`/`imagen`/`arrow_drop_down` 트리거, role=option 수집)를 어댑터로 이식.

## 2026-05-30 — Flow 2026 UI는 셀렉터 패치가 아니라 어댑터 재작업 (Phase B 발견)

- **발견**: 라이브 Flow UI(`labs.google/fx/ko/tools/flow`)가 기존 "Imagen 캔버스"(모델 드롭다운 → 종횡비 픽 → 4-variant 그리드 → variant별 다운로드)에서 **에이전트형 챗 UI**로 전면 개편됨. 진입 흐름이 바뀜:
  - 진입점: 단순 "Image" 버튼 없음 → **"새 프로젝트"** 버튼으로 프로젝트 생성 → 에이전트 세션("제목 없는 세션") 진입.
  - 설정: 프롬프트 바의 **`tune 설정` 기어** → **"에이전트 설정"** 패널 하나에 모두 통합 — 이미지 종횡비 탭(16:9/4:3/1:1/3:4/**9:16**), 출력 개수 탭(**1x~x4** → variant 수는 이제 여기서 정함), 이미지 모델 드롭다운, 동영상 기본값(16:9·9:16, 1x~x4, 모델), `저장` 버튼, "생성하기 전에 확인"(항상/안 함) 토글.
  - 생성: 프롬프트 입력 → `arrow_forward 만들기` 제출 → 결과가 **챗 스레드에 인라인**으로 도착(고정 4-up 그리드 아님). → `_wait_for_variants` / `_download_all_variants` 재작성 필요.
- **결정**: 기존 `_select_model` / `_select_aspect_ratio`(각각 "픽커 열고 옵션 클릭" 구조)는 새 통합 설정 패널과 안 맞음 → **flow_imagen.py 어댑터 재작업** 필요(설정 패널: 종횡비·개수·모델 설정 후 저장 → 프롬프트 → 제출 → 인라인 결과 수집·다운로드). flow_veo.py도 동일 패턴 예상.
- **미해결 결정 — 이미지 모델**: 새 Flow는 이미지 기본 모델이 **"🍌 Nano Banana 2"**. 프로젝트 기준 모델 **Imagen 4 Ultra가 기본이 아니며 드롭다운에서 아예 사라졌을 수 있음**. 다음 세션 첫 작업: 모델 드롭다운을 열어 실제 가용 모델 목록 확인 후 (a) Imagen 유지 가능 여부, (b) Nano Banana 2로 전환(project.yaml + 도구 정책 갱신, 상업이용 약관 확인) 결정. ⚠️ "도구 정책(변경 금지)"의 이미지 항목(Imagen 4 Ultra)에 영향 → 사용자 승인 후 갱신.
- **미해결 결정 — "생성하기 전에 확인"**: 이미지(무료)는 `안 함`(자동)으로 깔끔히 제출 권장(파이프라인 자체 게이트가 실질 통제점). s02 동영상(크레딧 소비) 전에 별도 재논의.
- **부수 수정 (이번 세션 커밋)**:
  - `cli.py`: cp949 등 비-UTF-8 콘솔에서 rich가 `•`/`—`/한글 출력 시 `UnicodeEncodeError`로 크래시 → 엔트리포인트에서 stdout/stderr를 UTF-8(`errors="replace"`)로 재설정. (이전 cp949 픽스는 파일 I/O 디코드 측, 이번은 콘솔 출력 인코드 측.)
  - `flow_imagen.py`: `open_image_tool`에 로케일 독립 셀렉터 프리펜드(`새 프로젝트|new project`, `add_2` 아이콘) — 통과 확인. `model_picker_open`에 `tune` 기어 셀렉터 프리펜드 — 통과 확인. 옛 영어 셀렉터는 하단 보존.
  - 참고: 첫 아이템에서 `tune` 버튼 미발견(타이밍 레이스) 1회 관찰 → 첫 네비게이션 후 대기/재시도 필요.
- **로케일 권고**: 영어 UI 강제(`/fx/en/`)는 비권장 — Flow는 이미 혼합 언어(`Flow`/`PRO`/`Create a character`는 영어, `새 프로젝트`/`닫기` 등은 한글)이고 계정 언어로 리다이렉트될 수 있어 불안정. **로케일 독립 셀렉터**(아이콘명 `add_2`/`tune`, `data-testid`, 한·영 정규식 병기)가 A/B·로케일 변화에 자가 치유적.

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
- 이미지: Google Flow **Imagen 4** (구 Imagen 4 Ultra는 Flow에서 사라짐 — 2026-05-31 결정 참조)
- 음악: Pixabay / YouTube Audio Library
- **금지**: Runway 무료, Suno/Udio 무료 (비상업 약관)
