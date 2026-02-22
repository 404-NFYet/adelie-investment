# Agent Shared-Control v3 변경 기록

## 1. 제품 관점 요약
- 목표: "화면을 보며 대화"에서 "화면을 함께 제어하는 에이전트"로 전환
- IA 유지: 하단 탭 `투자-홈-교육`, 프로필은 상단 아이콘 진입
- 핵심 UX
  - 하단 입력바는 항상 유지
  - 단순 이동/탭 전환은 캔버스 진입 없이 인라인 제어 트레이에서 즉시 실행
  - 분석/설명은 캔버스 화면에서 진행
  - 캔버스는 채팅 버블 대신 요약/근거/액션 중심 레이아웃

## 2. 앱기획방향 v3 반영 현황
### 2-1) 완료
- ChatFAB 제거 및 전역 하단 입력바(`AgentDock`) 도입
- 홈/투자에서 에이전트 진입점 연결
- 종목 상세 `이 종목 물어보기` CTA 연결
- 캔버스형 에이전트 화면(`/agent`) 및 대화 기록(`/agent/history`) 제공
- `context_text`에 화면 컨텍스트 전달 구조 도입

### 2-2) 이번 배치에서 강화
- 스트리밍 렌더 안정화(턴 분리 + 델타 정리)
- 홈 모드 한정 3단계 진행바, 기타 모드 상태점 단순화
- 인라인 제어 트레이(액션칩 + 상태) 및 주황 control pulse
- `ui_snapshot/action_catalog/interaction_state` 계약 정식화
- 문서 계층 분리(경험/계약/코브라우징)

### 2-3) 다음 단계
- 코-브라우징 실시간 동기화(이번엔 설계/스캐폴딩만)
- 백엔드 `ui_action` 실사용 생성 고도화
- 고위험 제어 승인 UX 강화(서명/이중 확인)

## 3. 사용자 여정 (화면별)
### 3-1) 홈
- 사용자가 홈 이슈를 확인
- 하단 트레이가 현재 컨텍스트 요약 + 빠른 액션 제안
- 단순 이동 명령은 인라인 즉시 실행
- 분석 질문은 캔버스로 전환되어 상세 응답

### 3-2) 투자
- 종목 상세에서 `이 종목 물어보기` 클릭
- 종목/보유 정보가 컨텍스트에 포함되어 캔버스로 전달
- 저위험 이동은 즉시, 고위험(매수/매도/외부 링크)은 확인 후 실행

### 3-3) 교육
- 선택 날짜/활동/브리핑 목록을 컨텍스트로 전달
- 하단 트레이에서 학습 이력/탭 전환 등 즉시 제어
- 상세 설명은 캔버스에서 처리

### 3-4) 캔버스
- 응답 턴 단위 스냅샷 탐색(위/아래 길게 스와이프)
- 일반 응답은 텍스트 우선 표시
- 구조화 신호가 있을 때만 key/bullet 섹션 확장

## 4. 제어 정책
### 4-1) 저위험 (즉시 실행)
- 라우팅/탭 이동
- 히스토리 진입
- 학습 아카이브 진입

### 4-2) 고위험 (확인 후 실행)
- 매수/매도 흐름 진입
- 외부 링크 오픈

### 4-3) 실패 처리
- 트레이 상태를 `error`로 표시
- 저위험 실패는 이전 경로 복구 시도
- 재시도 가능 액션은 동일 칩으로 재실행

## 5. 상태 머신
- `idle`: 대기
- `running`: 제어 실행 중 (`Agent control active`)
- `success`: 실행 완료
- `error`: 실행 실패

표시 계층:
- 하단: 인라인 트레이 상태 텍스트 + 주황 글로우 애니메이션
- 캔버스 상단: 컨텍스트 라인 + 상태 점 애니메이션

## 6. 코드 매핑
### 6-1) 오케스트레이션/트레이
- `frontend/src/hooks/useAgentControlOrchestrator.js`
- `frontend/src/components/agent/AgentInlineControlTray.jsx`
- `frontend/src/components/agent/AgentControlPulse.jsx`
- `frontend/src/components/agent/AgentDock.jsx`

### 6-2) 캔버스/스트리밍
- `frontend/src/pages/AgentCanvasPage.jsx`
- `frontend/src/components/agent/AgentCanvasSections.jsx`
- `frontend/src/components/agent/AgentStatusDots.jsx`
- `frontend/src/contexts/TutorChatContext.jsx`
- `frontend/src/contexts/TutorContext.jsx`
- `frontend/src/utils/agent/composeCanvasState.js`

### 6-3) 컨텍스트 계약 생성
- `frontend/src/utils/agent/buildUiSnapshot.js`
- `frontend/src/utils/agent/buildActionCatalog.js`
- `frontend/src/pages/Home.jsx`
- `frontend/src/pages/Portfolio.jsx`
- `frontend/src/pages/Education.jsx`

### 6-4) 백엔드 최소 보강
- `fastapi/app/api/routes/tutor.py`
- `fastapi/app/schemas/tutor.py`

## 7. QA 체크리스트
- [ ] 멀티턴 10회 이상에서 `Maximum update depth exceeded` 미발생
- [ ] 홈 모드에서만 3단계 진행바 노출
- [ ] stock/education 모드에서는 상태점만 노출
- [ ] 인라인 트레이에서 저위험 액션 즉시 실행
- [ ] 고위험 액션 확인 모달 노출
- [ ] 캔버스 일반 응답은 텍스트 우선 표시
- [ ] 같은 세션 스와이프 탐색(160px 임계) 동작
- [ ] `/agent/history` 목록/복원/삭제 동작
- [ ] `context_text`에 `ui_snapshot/action_catalog/interaction_state` 포함 확인
- [ ] `npm run build` 성공

## 8. 리스크 및 메모
- `context_text`가 커질수록 토큰/지연 증가 가능
- `ui_action` SSE는 현재 optional 계약(프론트 fallback 우선)
- `앱기획방향v3.md` 사용자 수정본은 변경하지 않음

## 9. 3차 통합 반영 (상황기반 분기 + Toss 톤 + 모델 속도)
### 문제 재현
- 텍스트 입력이 룰베이스 키워드(`종목`, `투자`)에 과매칭되어 의도치 않게 투자 탭 이동
- 액션 매칭 실패 시 `/agent`로 강제 전환되어 “항상 캔버스로 감”
- 캔버스 상단 정보가 과밀하여 본문 가독성 저하

### 의사결정
- 프론트 텍스트 파싱 제거, `/api/v1/tutor/route` 결정만 신뢰
- 인라인 트레이 칩은 최대 2개로 최소화
- 캔버스 헤더는 1줄 컴팩트 구성으로 축소
- Tutor 본응답 모델은 `gpt-5-mini`, reasoning effort는 `low` (환경변수)

### API 계약 변경
- 신규: `POST /api/v1/tutor/route`
  - request: `message`, `mode`, `context_text`, `ui_snapshot`, `action_catalog`, `interaction_state`
  - response: `decision`, `action_id`, `inline_text`, `canvas_prompt`, `confidence`, `reason`
- 기존 `/api/v1/tutor/chat` done 이벤트 확장
  - `model`, `reasoning_effort` 필드 포함

### UI 스크린 단위 변경
- Dock
  - 입력 시 항상 `/tutor/route` 호출
  - `inline_action` 즉시 실행, `inline_reply`는 1줄 메시지 노출, `open_canvas`만 캔버스 전환
  - 라우터 실패 시 자동 캔버스 전환 금지 + “캔버스 열기” 보조 버튼 제공
- Canvas
  - 상단 1줄: 뒤로가기/타이틀/상태점/정보/기록
  - 긴 컨텍스트 문구는 접힘 정보영역으로 이동
  - 스와이프 안내는 핸들 + `n/m` + 토스트 중심으로 단순화
- Style
  - 에이전트 전용 토큰(`--agent-*`) 추가
  - 얇은 보더/약한 그림자/작은 반경으로 톤 정리

### 왜 바꿨는지
- 사용자의 실제 의도와 다른 자동 이동을 막고, 상황 기반 전환으로 제어 신뢰도를 높이기 위해

### 사용자가 체감하는 변화
- “아무거나 눌렀는데 투자 탭으로 이동” 현상 감소
- 입력 후 무조건 캔버스 전환이 아닌, 인라인 처리와 캔버스 전환이 자연스럽게 분리
- 상단이 덜 가려지고 화면이 가볍고 정돈된 느낌으로 개선

### 코드 위치
- 백엔드 라우팅/모델: `fastapi/app/api/routes/tutor.py`, `fastapi/app/schemas/tutor.py`, `fastapi/app/core/config.py`
- 프론트 분기/트레이: `frontend/src/components/agent/AgentDock.jsx`, `frontend/src/hooks/useAgentControlOrchestrator.js`, `frontend/src/utils/agent/buildActionCatalog.js`
- 캔버스/스타일: `frontend/src/pages/AgentCanvasPage.jsx`, `frontend/src/components/agent/AgentInlineControlTray.jsx`, `frontend/src/components/agent/AgentStatusDots.jsx`, `frontend/src/components/layout/BottomNav.jsx`, `frontend/src/styles/globals.css`

### 검증 결과
- [ ] 홈에서 임의 문장 입력 시 오탐 이동이 재현되지 않는지
- [ ] 입력 후 `inline_action|inline_reply|open_canvas` 분기 동작
- [ ] `/tutor/route` 장애 시 인라인 fallback + 캔버스 보조 버튼 동작
- [ ] 캔버스 상단 1줄 유지 및 본문 가림 없음
- [ ] `npm run build` 성공

## 10. Toss 톤 UI 리디자인 (스타일 전용)

### 왜 바꿨는지
- 상단 헤더가 2줄 이상 차지하여 모바일 본문 가독성 저하
- 트레이/독 높이가 과도하여 입력 영역이 화면을 많이 차지
- 글로우/그림자가 강해서 전체적으로 과장된 느낌
- 안내 문구가 과다하여 Toss 톤(단순·밀도 낮음·명확한 계층)과 괴리

### 사용자가 체감하는 변화
- 헤더가 h-14 → h-11로 축소, 정보/기록 버튼은 아이콘 전환 → 본문 노출 면적 증가
- "AI가 보고 있는 것..." 문구 기본 숨김, info 아이콘 탭 시에만 노출
- 스와이프 영역이 카드 → 미니 핸들(h-8) + `n/m` 텍스트로 축소
- 하단 독 높이 96px → 52px, 입력폼 h-11 원형 경량화
- 트레이 액션칩 최대 2개, 상태 텍스트 1줄 말줄임
- 글로우/그림자 대폭 약화, 카드 보더 #E8EBED 통일
- 색상 팔레트 Toss 그레이(#191F28, #333D4B, #4E5968, #8B95A1, #B0B8C1, #D1D6DB, #E8EBED, #F2F4F6, #F7F8FA)로 정리
- 주황(#FF6B00)은 CTA/active 상태에서만 사용

### 코드 위치
- `frontend/src/styles/globals.css` — agent 전용 CSS 토큰 추가/정리 (`--agent-dock-h`, `--agent-shadow`, `--agent-bg-page` 등)
- `frontend/src/pages/AgentCanvasPage.jsx` — 1줄 컴팩트 헤더, info/history 아이콘화, 스와이프 미니 핸들
- `frontend/src/components/agent/AgentDock.jsx` — 독 높이 축소, 입력폼 경량화
- `frontend/src/components/agent/AgentInlineControlTray.jsx` — 트레이 py 축소, 액션칩 2개 제한, 상태 1줄
- `frontend/src/components/agent/AgentCanvasSections.jsx` — 카드 반경/보더/그림자 통일, 과도한 장식 제거
- `frontend/src/components/agent/AgentControlPulse.jsx` — radial-gradient 제거, 약한 shadow만 유지
- `frontend/src/components/agent/AgentStatusDots.jsx` — dot 크기/간격 미세 조정

### 검증 결과
- [x] `npm run build` 성공
- [ ] 모바일에서 상단/하단이 본문 가리지 않는지 확인
- [ ] 홈/투자/교육/agent/history 레이아웃 일관성 확인

## 11. 독-네비 분리 및 세션 복귀 UX

### 왜 바꿨는지
- 하단 독(AgentDock)과 BottomNav가 시각적으로 겹치고 기능도 중복(탭 이동 액션칩 등)
- InlineControlTray가 독 위에 쌓여 하단 영역이 과도하게 커짐
- 캔버스 진입 후 중간에 나갔을 때 대화 복귀 흐름이 없었음

### 사용자가 체감하는 변화
- 독이 볼드한 카드 형태(`rounded-[20px]`, `shadow 0_2px_12px`)로 네비와 시각적으로 확실히 분리
- InlineControlTray 스택 제거 — 인라인 메시지는 독 안에 조건부 1줄로만 표시
- 진행 중인 대화가 있으면 독 상단에 "진행 중인 대화가 있어요" 복귀 바 노출, 탭하면 /agent로 이동
- 네비 기능 중복 제거: `nav_home/nav_portfolio/nav_education` 액션칩이 트레이에 더 이상 노출되지 않음
- 입력폼 높이 h-12, 버튼 h-8로 키워서 터치 영역 확대

### 코드 위치
- `frontend/src/components/agent/AgentDock.jsx` — 전면 재설계: 트레이 인라인화, 세션 복귀 바, 볼드 카드 스타일
- `frontend/src/hooks/useAgentControlOrchestrator.js` — `suggestedActions`에서 nav 타입 액션 필터링
- `frontend/src/components/agent/AgentInlineControlTray.jsx` — 독에서 더 이상 import하지 않지만 파일은 유지 (다른 곳에서 사용 가능)

### 검증 결과
- [x] `npm run build` 성공
- [ ] 독-네비 간 시각적 분리 확인
- [ ] 세션 복귀 흐름 확인 (홈에서 독 탭 → /agent 복귀)
- [ ] 캔버스에서 네비 중복 CTA 미노출 확인

## 12. Agent UX 4차 실행 (스트리밍/검색/복습/레이아웃)

### 문제 재현
- 하단 입력바에 기록 버튼이 없어 `/agent/history` 접근 경로가 약함
- 페이지 하단 padding이 각기 달라 본문과 독/네비가 겹칠 수 있음
- 홈 `오늘의 이슈` 아이콘이 고정 펭귄으로 렌더되어 키워드 아이콘 체계 미반영
- 캔버스가 plain text 렌더 중심이라 markdown 응답 표현력이 낮음
- `gpt-5-mini` 경로에서 stream 체감이 불안정(완료 후 몰아쓰기 케이스)
- 복습 카드가 학습 진도와 연결되지 않아 교육 탭에서 복습 루프가 약함

### 의사결정
- `Responses API` 기반 스트리밍 우선, 실패 시 chat.completions 폴백
- 인터넷 검색은 Dock 토글 + `use_web_search`로 제어
- 캔버스만 markdown 렌더, inline/dock은 plain 유지
- 구조화는 완료 후 보조 추출(`summary`, `key_points`, `suggested_actions`)
- 복습 저장은 `learning_progress` 참조형 재사용(스키마 변경 없음)

### API 계약 변경
- `POST /api/v1/tutor/chat` request 필드 확장
  - `use_web_search?: boolean`
  - `response_mode?: "plain" | "canvas_markdown"`
  - `structured_extract?: boolean`
- `done` 이벤트 확장
  - `search_used`, `response_mode`, `structured` (옵션)
- `TutorChatEvent` 스키마에 위 필드 반영
- `canvas_markdown` 모드일 때 백엔드 시스템 프롬프트에 Markdown 형식 지시(요약/불릿/다음 액션) 강제

### UI 스크린 단위 변경
- Dock
  - 검색 토글(지구본) + 기록 버튼(시계) 항상 노출
  - 기록 버튼 탭 시 `/agent/history` 이동
  - 검색 토글 상태 `localStorage(adelie_agent_web_search)` 저장
- 레이아웃
  - 홈/투자/교육/agent/history/agent 본문 하단 padding을 `calc(var(--bottom-nav-h)+var(--agent-dock-h)+16px)`로 통일
  - `--agent-dock-h`를 104px로 조정
- Home
  - 오늘의 이슈 아이콘을 `issueCard.icon_key` 기반으로 복구
  - 기존 미션 카드 레이아웃을 “대화 정리 카드(최근 세션)” 데이터 소스로 재활용
- Canvas
  - `ReactMarkdown + remarkMath + rehypeKatex` 렌더 적용
  - 완료 이벤트의 `structured`가 있으면 요약/포인트 보조 카드 노출
- Education
  - `learning_progress` 기반 복습 카드 섹션 추가
  - `review_meta:{content_type}:{content_id}` 로컬 메타(sidecar) 반영
  - `복습 완료` 버튼으로 `completed/100` 업데이트

### 왜 바꿨는지
- “하단 진입성”, “gpt-5 스트리밍 안정성”, “복습 루프”를 한 번에 연결해 사용자 흐름(질문 → 요약 → 복습)을 닫기 위해

### 사용자가 체감하는 변화
- 입력바에서 바로 기록 확인 가능
- 하단 UI와 본문 겹침 감소
- 오늘의 이슈 카드의 아이콘 일관성 복구
- 캔버스 답변이 markdown(헤딩/리스트/강조/수식)으로 읽기 쉬워짐
- 최근 대화가 홈 카드로 요약되어 재진입 쉬움
- 교육 탭에서 복습 카드 확인/완료 처리 가능

### 코드 위치
- 백엔드
  - `fastapi/app/schemas/tutor.py`
  - `fastapi/app/core/config.py`
  - `fastapi/app/api/routes/tutor.py`
- 프론트
  - `frontend/src/components/agent/AgentDock.jsx`
  - `frontend/src/contexts/TutorChatContext.jsx`
  - `frontend/src/contexts/TutorContext.jsx`
  - `frontend/src/pages/AgentCanvasPage.jsx`
  - `frontend/src/components/agent/AgentCanvasSections.jsx`
  - `frontend/src/utils/agent/composeCanvasState.js`
  - `frontend/src/pages/Home.jsx`
  - `frontend/src/pages/Education.jsx`
  - `frontend/src/pages/Portfolio.jsx`
  - `frontend/src/pages/AgentHistoryPage.jsx`
  - `frontend/src/styles/globals.css`
- 문서
  - `docs/agent/agent-ui-design-handoff-v1.md`
  - `docs/agent/agent-control-contract-v1.md` (Responses API vs 기존 경로 비교, SSE 매핑/디버깅 기준 추가)

### 검증 결과
- [ ] 하단바 기록 버튼 상시 노출 및 `/agent/history` 이동 확인
- [ ] 검색 토글 ON/OFF가 `/api/v1/tutor/chat` 요청에 반영되는지 확인
- [ ] `gpt-5-mini`에서 stream delta 실시간 렌더 확인
- [ ] 캔버스 markdown 렌더(리스트/강조/수식) 확인
- [ ] 홈 대화 정리 카드 클릭 시 세션 복원 확인
- [ ] 교육 복습 카드 표시/완료 처리 확인
- [ ] `npm run build` 성공

## 13. Agent UX 5차 실행 (좌우 탐색 + 선택 질문 + 소프트 가드레일 + 이슈 캐러셀)

### 문제 재현
- 캔버스 이전 대화 탐색이 세로 당김 기반이라 오동작/발견성이 낮음
- 본문 일부 문장을 바로 후속 질문으로 보내는 인터랙션 부재
- 가드레일이 ADVICE/OFF_TOPIC까지 강차단되어 대화 연속성이 떨어짐
- Dock 상단 라인이 세션 있을 때만 보여서 빈 상태 가이드가 약함
- 홈 오늘의 이슈가 단일 카드라 `final briefings` 3개 흐름을 충분히 활용하지 못함

### 의사결정
- 캔버스 탐색은 `좌우 반투명 버튼 + 좌우 스와이프` 병행
- 선택 질문은 `텍스트 선택형`으로 캔버스/홈 이슈에 적용
- 가드레일 정책 기본값을 `soft`로 전환 (`MALICIOUS`만 hard block)
- Dock 상단 라인은 항상 노출, 우측에 검색/기록 토글 배치
- 오늘의 이슈는 3카드 캐러셀 + 자동 롤(4.5초) + 사용자 터치 시 세션 내 정지

### API 계약 변경
- `/api/v1/tutor/chat` SSE `step` 타입 확장:
  - `guardrail_notice`
- `/api/v1/tutor/chat` `done` 필드 확장:
  - `guardrail_decision`
  - `guardrail_mode`
- 백엔드 설정 추가:
  - `TUTOR_GUARDRAIL_POLICY=soft|strict` (기본 `soft`)

### UI 스크린 단위 변경
- Canvas
  - 세로 탐색 제거, 좌우 탐색으로 전환
  - 좌우 overlay 버튼(반투명) 추가
  - 선택 텍스트 `이 부분 질문` 칩 추가
- Home
  - 오늘의 이슈 3카드 캐러셀화
  - 좌우 버튼/스와이프/도트 인디케이터 추가
  - 자동 전환 + 터치 후 자동 정지
  - 이슈 텍스트 선택 질문 칩 추가
- Dock
  - 상단 라인 항상 노출
  - 세션 유무에 따라 오렌지/그린 상태 라인 분기
  - 검색/기록 아이콘을 상단 라인 우측으로 이동

### 코드 위치
- 백엔드
  - `fastapi/app/core/config.py`
  - `fastapi/app/services/guardrail.py`
  - `fastapi/app/schemas/tutor.py`
  - `fastapi/app/api/routes/tutor.py`
- 프론트
  - `frontend/src/pages/AgentCanvasPage.jsx`
  - `frontend/src/components/agent/AgentCanvasSections.jsx`
  - `frontend/src/components/agent/AgentDock.jsx`
  - `frontend/src/contexts/TutorChatContext.jsx`
  - `frontend/src/pages/Home.jsx`
  - `frontend/src/components/agent/SelectionAskChip.jsx` (신규)
  - `frontend/src/hooks/useSelectionAskPrompt.js` (신규)
- 문서
  - `docs/agent/agent-experience-spec-v1.md`
  - `docs/agent/agent-control-contract-v1.md`
  - `docs/agent/agent-ui-design-handoff-v1.md`

### 검증 결과
- [ ] 캔버스 좌우 버튼/좌우 스와이프로 턴 이동 확인
- [ ] 캔버스/홈 이슈 텍스트 선택 질문 칩 동작 확인
- [ ] Dock 상단 라인 상시 노출 + 검색/기록 아이콘 위치 확인
- [ ] 오늘의 이슈 캐러셀 자동 롤 + 터치 후 정지 확인
- [ ] ADVICE/OFF_TOPIC 입력 시 soft notice 후 응답 진행 확인
- [ ] MALICIOUS 입력 시 hard block 유지 확인
- [ ] `done.guardrail_decision/guardrail_mode` 값 수신 확인

### 이번 배치 실제 반영 포인트 (요약)
- 캔버스
  - 세로 스와이프 제거, 좌우 스와이프/버튼으로 탐색 전환
  - 선택 텍스트를 즉시 후속 질문으로 전송하는 플로팅 칩 추가
- 홈
  - 오늘의 이슈를 최대 3개 캐러셀로 구성
  - 4.5초 자동 전환 + 사용자 인터랙션 시 세션 내 자동정지
  - 이슈 텍스트 선택 질문 칩 추가
- Dock
  - 상단 상태 라인 상시 노출
  - 세션 없음: 초록 안내 문구, 세션 있음: 진행 중 대화 복귀 라인
  - 검색/기록 토글을 상단 라인 우측으로 이동
- 가드레일
  - 정책 기본값 `soft`
  - `MALICIOUS`만 hard block, `ADVICE/OFF_TOPIC`은 `guardrail_notice` 후 응답 지속
  - `done.guardrail_decision`, `done.guardrail_mode` 메타 반환

### 5차 반영 파일 목록
- 백엔드
  - `fastapi/app/core/config.py`
  - `fastapi/app/services/guardrail.py`
  - `fastapi/app/schemas/tutor.py`
  - `fastapi/app/api/routes/tutor.py`
- 프론트
  - `frontend/src/pages/AgentCanvasPage.jsx`
  - `frontend/src/components/agent/AgentCanvasSections.jsx`
  - `frontend/src/components/agent/AgentDock.jsx`
  - `frontend/src/components/agent/AgentStatusDots.jsx`
  - `frontend/src/contexts/TutorChatContext.jsx`
  - `frontend/src/pages/Home.jsx`
  - `frontend/src/hooks/useSelectionAskPrompt.js` (신규)
  - `frontend/src/components/agent/SelectionAskChip.jsx` (신규)
- 문서
  - `docs/agent/agent-experience-spec-v1.md`
  - `docs/agent/agent-control-contract-v1.md`
  - `docs/agent/agent-ui-design-handoff-v1.md`

## 14. Agent UX 6차 실행 (sync-first + 중단/재생성 + Dock/네비 안정화)

### 문제 재현
- develop와 feature 브랜치가 서로 갈라져 있어 최신 테스트/인프라 변경을 반영하지 못한 상태
- 캔버스에서 `chatOptions`가 `useTutor.sendMessage` 경유 중 누락되어 `response_mode/use_web_search/structured_extract` 체감 미반영
- 생성 중단/재생성이 없어 멀티턴 중 제어권이 약함
- Dock 문구가 `/agent`에서도 고정형이라 현재 상태를 설명하지 못함
- 입력 중 모바일에서 하단 네비가 같이 보여 가림/겹침 발생
- 홈 대화 정리 카드가 세션 메타(icon/keyword/snippet)를 충분히 재활용하지 못함

### 의사결정
- sync-first: `origin/develop`를 현재 브랜치에 먼저 merge 후 기능 수정 진행
- 충돌 파일 2개(`AgentDock`, `AgentCanvasSections`)는 프론트 현재 브랜치 UX 우선으로 수동 정리
- 생성 제어는 프론트 `AbortController` 기반으로 구현(외부 API 변경 없음)
- Dock는 상태 중심 문구 + 주황 글로우 강화
- 입력 포커스/키보드 상태에서 BottomNav 숨김, Dock는 키보드 상단으로 보정
- 세션 메타는 DB 변경 없이 localStorage 참조형(`session_meta:{session_id}`)으로 저장/재사용

### 구현 상세
- Sync
  - `Merge remote-tracking branch 'origin/develop' into feat/agent-canvas-v3-yj99son` 완료
  - 충돌 수동 해결: `frontend/src/components/agent/AgentDock.jsx`, `frontend/src/components/agent/AgentCanvasSections.jsx`
- 중단/재생성
  - `TutorChatContext`에 `activeStreamControllerRef`, `lastRequestRef`, `isStreamingActive`, `canRegenerate` 추가
  - `stopGeneration()`/`regenerateLastResponse()` 추가
  - 중단 시 부분 텍스트 유지 + 턴 상태 `stopped`
- 렌더링 누락 원인 수정
  - `TutorContext.sendMessage` 시그니처 확장: `options.chatOptions`, `options.contextInfoOverride` 지원
  - `AgentCanvasPage`에서 `sendCanvasMessage()`로 `chatOptions + contextInfoOverride` 강제 전달
- Dock 개선
  - `/agent`에서 상단 라인을 상태 문구(`분석 중`, `답변 생성 중`, `중단됨`, `대기 중`)로 전환
  - 세션 없음 문구 단축(`질문하세요`, `한 줄로 물어보세요`)
  - `AgentControlPulse`/`globals.css`로 주황 글로우 가시성 강화
- 네비 숨김/키보드 보정
  - 신규 훅 `frontend/src/hooks/useKeyboardInset.js`
  - `AgentDock`에서 `--keyboard-offset` 적용
  - `BottomNav`는 `inputFocused || keyboardOpen`이면 숨김
- 대화 정리 카드 메타
  - 신규 유틸 `frontend/src/utils/agent/sessionCardMetaStore.js`
  - `TutorChatContext` 완료/중단 시 세션 메타 저장
  - `Home`에서 세션 메타(`icon_key`, `keywords[]`, `snippet`) 읽어 카드 렌더

### API/내부 인터페이스 변경
- 외부 API
  - 없음 (`/api/v1/tutor/chat`, `/api/v1/tutor/route` 유지)
- 내부 인터페이스
  - `useTutor.sendMessage(message, difficulty, options?)`
    - `options.chatOptions`
    - `options.contextInfoOverride`
  - `useTutor`/`useTutorChat` 추가 노출
    - `stopGeneration()`
    - `regenerateLastResponse()`
    - `isStreamingActive`
    - `canRegenerate`

### 검증 결과
- [x] sync-first merge 완료(충돌 2개 수동 해결)
- [x] 캔버스 헤더 중단/재생성 버튼 반영
- [x] `chatOptions/contextInfoOverride` 전달 경로 반영
- [x] `/agent` Dock 상태 문구 전환 및 짧은 안내 문구 반영
- [x] 입력 포커스/키보드 상태에서 BottomNav 숨김 로직 반영
- [x] 세션 메타 저장/홈 카드 재활용 경로 반영
- [ ] `npm run build` 검증
- [ ] 수동 플로우(홈 -> agent -> 중단/재생성 -> history -> 홈 카드 복귀) 검증

## 13. Agent UX 7차 + 투자엔진 확장 통합 반영 (v7)

### 문제 재현
- 모바일 입력 중 BottomNav가 아닌 환경에서도 함께 숨겨지는 경우가 있어 데스크톱 가시성이 저하됨
- 캔버스에서 상태/근거는 보이지만 투자 질문에서 공시/수치 근거가 일관되게 연결되지 않음
- 시뮬레이션 체결이 단순 정가 체결이라 상한가/저유동성 시나리오의 현실성이 부족함
- 대화 요약 카드는 로컬 메타 중심이라 서버 세션 메타와 정렬이 약함

### 의사결정
- BottomNav 숨김은 `모바일 + 키보드/포커스` 조건으로 제한
- Dock 글로우/스파클은 스트리밍/제어 중 상태 강조용으로 강화하고 dev에서 튜닝 가능하게 유지
- stock 모드는 내부 데이터 + OpenDART + web_search를 혼합 근거로 사용
- 체결 모델은 슬리피지/유동성 cap/지정가 pending/부분체결/short·leverage를 허용하는 현실형 시뮬레이션으로 전환
- 세션 저장 메타는 서버 `tutor_sessions` 확장값 우선, 로컬 sidecar fallback

### 구현 상세
- 프론트
  - `useKeyboardInset`에서 `shouldHideBottomNav`를 모바일 조건(`max-width + pointer coarse`)으로 제한
  - `AgentDock` 주황 글로우/스파클 강화 및 dev glow tuner 제공
  - `AgentCanvasPage` 홈 모드 상단을 1줄 긴 progress bar로 전환, 헤더 `저장` 버튼(세션 pin) 추가
  - `Home` 대화 정리 카드에서 서버 메타(`cover_icon_key`, `summary_keywords`, `summary_snippet`, `is_pinned`) 우선 렌더
  - `composeCanvasState`/`AgentCanvasSections`에 근거 출처 블록 + OpenDART 핵심 수치 블록 추가
- 백엔드
  - `investment_intel` 기반으로 stock 모드에서 내부 브리핑/리포트 + OpenDART 수치 수집
  - `/tutor/chat` done에 `sources`를 `source_kind`/`is_reachable` 포함 형태로 정규화하고 web_search 사용 시 웹 근거 메타 보강
  - `portfolio_service.execute_trade` 현실형 체결 로직으로 교체
    - 시장가/지정가
    - 슬리피지/수수료
    - 유동성 cap 기반 부분체결
    - `pending|partial|filled`
    - `long|short`, 최대 2x leverage, short 차입수수료 누적
  - `tutor_sessions` 메타 확장 및 pin API 추가
    - `POST /api/v1/tutor/sessions/{session_id}/pin`

### API/DB 변경
- API 확장
  - `/api/v1/tutor/sessions` 응답에 `cover_icon_key`, `summary_keywords`, `summary_snippet`, `is_pinned`, `pinned_at` 추가
  - `/api/v1/tutor/sessions/{id}/messages` 응답에 세션 메타 필드 추가
  - `/api/v1/tutor/sessions/{id}/pin` 신규
  - `/api/v1/tutor/chat` done의 `sources[]`에 `source_kind`, `is_reachable` 보강
  - 포트폴리오/트레이딩 응답에 실행 메타(`requested_price`, `executed_price`, `slippage_bps`, `fee_amount`, `order_kind`, `order_status`, `position_side`, `leverage`, `filled_quantity`, `remaining_quantity`) 반영
- DB 마이그레이션
  - 신규: `database/alembic/versions/20260222_agent_v7_execution_and_session_meta.py`
  - `portfolio_holdings`: `position_side`, `leverage`, `borrow_rate_bps`, `last_funding_at`
  - `simulation_trades`: `filled_quantity`, `requested_price`, `executed_price`, `slippage_bps`, `fee_amount`, `order_kind`, `order_status`, `position_side`, `leverage`
  - `tutor_sessions`: `cover_icon_key`, `summary_keywords`, `summary_snippet`, `is_pinned`, `pinned_at`

### 검증 결과
- [x] `npm run build` 성공
- [x] 변경 백엔드/마이그레이션 파일 문법 파싱 성공(`ast.parse`)
- [ ] Alembic 실제 업그레이드 실행 검증
- [ ] 거래 시나리오(상한가/저유동성/short/2x) API smoke
- [ ] 홈 카드 pin/복원 실기기 확인

## 15. 기획 외 확장사항 상세 문서화 (v7 기준)

이 섹션은 `앱기획방향v3.md` 원문에 직접 명시되지 않았지만, 실험 브랜치에서 요구사항/버그/현실화 이슈로 인해 추가된 확장사항을 정리한 기록입니다.

### 15-1. 왜 "기획 외 확장"이 필요했는가
- 원문 기획은 "에이전트 전환 방향" 중심이라, 실제 운영에서 반드시 필요한 체결 현실화/세션 저장 메타/링크 검증/입력 레이아웃 안정화까지는 범위를 구체화하지 않았음.
- 사용자 피드백에서 "보기 좋은 UI"보다 "실제로 믿고 쓸 수 있는 결과"(체결 현실성, 출처 신뢰성, 복습 자산화) 요구가 강하게 확인됨.
- 따라서 v7은 기획 의도를 깨지 않으면서, 운영 가능한 제품으로 가기 위한 보강층을 추가함.

### 15-2. 제품 기획 관점(PO/PM)
- 추가 목표
  - 답변 품질 신뢰도 강화: 출처 종류/링크 유효성/수치 근거 제공.
  - 시뮬레이션 신뢰도 강화: 단순 체결 모델 탈피.
  - 학습 지속성 강화: 대화 결과를 카드 자산으로 축적.
- 기대 효과
  - "정보성 대화"에서 "행동 가능한 인사이트"로 전환.
  - "그때그때 대화"에서 "누적 학습 자산"으로 전환.
  - 홈 재방문 시 재진입 동선(저장 카드) 강화.

### 15-3. 사용자 경험 관점(UX)
- 문제
  - 입력 시 하단 요소 충돌, 상태 문구 혼재, 캔버스 근거 부족.
- 개선
  - 모바일만 BottomNav 숨김 + Dock 고정 가시성 유지.
  - 캔버스 홈 모드 긴 진행바, 기타 모드 상태점 분리.
  - 캔버스에 근거 출처 카드/핵심 수치 카드 표시.
  - `저장` 버튼으로 세션 고정, 홈 카드에서 즉시 재진입.
- 체감 변화
  - 입력 중 화면이 덜 가려짐.
  - "왜 이 답변인지"를 출처/수치로 확인 가능.
  - 좋은 대화를 잃지 않고 다시 불러올 수 있음.

### 15-4. 투자 도메인 관점(시뮬레이션 정확도)
- 문제
  - 기존 정가 체결은 상한가/저유동성에서 비현실적.
- 확장
  - 슬리피지, 수수료, 유동성 cap, 부분체결 반영.
  - 지정가 미체결/부분체결 상태(pending/partial) 반영.
  - KR 공매도(short) + 최대 2x 레버리지 MVP 반영.
  - short 포지션 차입수수료 누적 정산.
- 한계
  - 백테스트 엔진 수준의 미세 미시구조(호가 스냅샷 기반)까지는 아님.
  - 미국/ETF/옵션 파생상품은 이번 범위 제외.

### 15-5. 데이터/LLM 관점
- 컨텍스트 소스 계층
  - 1순위: 내부 브리핑/리포트/DB
  - 2순위: OpenDART 공시·재무수치
  - 3순위: web_search 보강(토글 ON)
- 응답 계약 보강
  - `sources[].source_kind`로 근거 타입 명시.
  - `sources[].is_reachable`로 링크 접근성 명시.
  - 캔버스는 markdown 원문 + 보조 구조화 + 수치 블록 병행.

### 15-6. 백엔드 아키텍처 관점
- 신규/핵심 모듈
  - `investment_intel.py`: stock 모드 근거 수집 계층.
  - `portfolio_service.execute_trade`: 현실형 체결 엔진.
  - `tutor_sessions pin API`: 세션 고정/해제.
- 확장 원칙
  - 외부 공개 경로는 유지(`POST /api/v1/tutor/chat`, `/route`).
  - 내부 메타만 점진 확장(하위호환 유지).

### 15-7. DB/마이그레이션 관점
- 추가 컬럼
  - `portfolio_holdings`: `position_side`, `leverage`, `borrow_rate_bps`, `last_funding_at`
  - `simulation_trades`: `filled_quantity`, `requested_price`, `executed_price`, `slippage_bps`, `fee_amount`, `order_kind`, `order_status`, `position_side`, `leverage`
  - `tutor_sessions`: `cover_icon_key`, `summary_keywords`, `summary_snippet`, `is_pinned`, `pinned_at`
- 원칙
  - 기존 long 1x 흐름을 기본값으로 유지하여 하위호환 보장.

### 15-8. 운영/모니터링 관점(SRE)
- 추천 모니터링 지표
  - 튜터 응답 완료율, 평균 첫 델타 도달 시간, web_search 사용률.
  - source reachable 실패율.
  - trade `partial/pending` 비율, short 포지션 비율, 강제 청산 근접 경고 수.
- 운영 체크
  - OpenDART 키 미설정 시 graceful fallback 여부.
  - web_search OFF 기본 정책(투자 모드만 ON 기본) 준수 여부.

### 15-9. 컴플라이언스/리스크 관점
- 유지된 안전 원칙
  - 직접 매수/매도 권유 금지.
  - `MALICIOUS` hard block.
- 완화된 정책
  - `ADVICE`, `OFF_TOPIC`은 대화를 끊지 않고 soft notice 후 교육형 전환.
- 잠재 리스크
  - 공시/웹 근거 최신성 차이로 인한 시점 불일치.
  - short/leverage UX 오해 가능성(고위험 상품 인식 부족).

### 15-10. QA 관점 (기획 외 항목 전용)
- 기능
  - 모바일 키보드 open 시 BottomNav 숨김, 데스크톱 유지.
  - 캔버스 저장 버튼 -> 세션 pin -> 홈 카드 상단 "저장됨" 반영.
  - stock 질문에서 DART 수치 블록/근거 링크 표시.
- 거래
  - 저유동성 주문에서 partial 발생 확인.
  - 지정가 미체결에서 pending 상태 확인.
  - short open/cover 시 손익/수수료/차입비용 반영 확인.
- 회귀
  - 기존 long 1x 시장가 주문 정상 동작.
  - history 복원/삭제/pin 동작.

### 15-11. 롤백 전략
- 즉시 롤백 가능 계층
  - 프론트 표시 레이어(수치/출처 카드) 비활성.
  - 세션 pin 버튼 숨김.
- 부분 롤백 계층
  - trade 엔진에서 short/leverage 경로 플래그 off.
  - 슬리피지/유동성 모델 계수 축소.
- DB 롤백
  - Alembic downgrade 가능하나, 운영 데이터 손실 위험 고려해 비파괴 롤백 우선 권장.

### 15-12. 아직 남은 항목
- Alembic 실 DB 적용 검증/롤백 검증.
- 실거래와의 괴리율 관측 후 슬리피지/유동성 파라미터 튜닝.
- 복습 카드의 서버-클라이언트 메타 정합성 주기 점검.
- 투자 캔버스 차트 생성 실패 fallback UX 개선.

## 16. 계산 로직/하드코딩/목업 감사 기록 (v7 추가)

### 16-1. 감사 범위
- 목적: "어떤 값이 계산식인지", "어떤 값이 하드코딩인지", "임시 목업/폴백이 남아있는지"를 분리해 명시
- 범위:
  - 백엔드: `portfolio_service`, `tutor`, `investment_intel`, `guardrail`, `config`
  - 프론트: `Home`, `AgentCanvasPage`, `AgentDock`, `useKeyboardInset`, `composeCanvasState`, `buildActionCatalog`
- 비범위:
  - 파이프라인 생성 로직(`final_briefings`) 원본 알고리즘 자체 변경/재검증
  - 실거래 백테스트 수준의 체결 정합성 검증

### 16-2. 계산 로직 상세 (공식/룰)

| 영역 | 계산식/룰 | 코드 위치 | 상수 의존 | 메모 |
|---|---|---|---|---|
| 체결 가능 수량 | `max_fill = int(volume * 0.12)`, 상/하한 근접 방향 압력 시 `max_fill *= 0.35`, `executed_qty = min(requested, max_fill)` | `fastapi/app/services/portfolio_service.py:60` | `MAX_MARKET_PARTICIPATION=0.12`, `PRICE_LIMIT_NEAR_PCT=28.5` | 유동성/상한가 체결 비현실성 완화용 휴리스틱 |
| 슬리피지 | `bps = 6 + participation 페널티 + 저유동성(8bps) + 상/하한 근접(16bps)` | `fastapi/app/services/portfolio_service.py:93` | `BASE_SLIPPAGE_BPS=6.0`, `LOW_LIQUIDITY_VOLUME=10000` | 실거래 체결모델이 아닌 시뮬레이션 근사 |
| 체결가 | `executed = current_price * (1 ± bps/10000)`, 지정가면 buy는 상한 clip, sell은 하한 clip | `fastapi/app/services/portfolio_service.py:118` | 슬리피지 상수 사용 | 지정가 즉시체결 조건과 함께 동작 |
| 롱 포지션 현금흐름 | 신규매수: `cash_needed = (notional/leverage) + fee`<br>청산: `cash_delta = margin_release + pnl - fee` | `fastapi/app/services/portfolio_service.py:358` | `MAX_LEVERAGE=2.0`, `BASE_FEE_RATE=0.00015` | 레버리지 1~2x 범위 |
| 숏 포지션 차입비용 | `cost = (avg_price*qty) * (borrow_bps/10000) * elapsed_days` | `fastapi/app/services/portfolio_service.py:204` | `SHORT_DEFAULT_BORROW_BPS=8` | 일할 누적 차입수수료 |
| 숏 청산 손익 | `pnl = (base_price - executed_price) * qty` | `fastapi/app/services/portfolio_service.py:442` | 레버리지/수수료 상수 사용 | 손실 과다 시 경고 로그만 남김 |
| 보상 배수 | 만기 시 `profit > 0`이면 `bonus = base_reward*(1.5-1.0)` 추가 지급 | `fastapi/app/services/portfolio_service.py:555` | `PROFIT_MULTIPLIER=1.5`, `REWARD_MATURITY_DAYS=7` | 브리핑 보상 정책 상수 |
| 홈 학습 진행률 | `weekProgress = round((activeDays/7)*100)` | `frontend/src/pages/Home.jsx:80` | 분모 7 고정 | 주간 뷰 기준 단순 진행률 |
| 이슈 캐러셀 자동롤 | 4.5초 간격 자동 전환, 사용자 터치 시 세션 내 정지 | `frontend/src/pages/Home.jsx:23` | `ISSUE_AUTO_ADVANCE_MS=4500` | UX 정책 상수 |
| 캔버스 턴 스와이프 | `abs(deltaX) >= 86px`일 때만 턴 이동 | `frontend/src/pages/AgentCanvasPage.jsx:15` | `HORIZONTAL_SWIPE_THRESHOLD_PX=86` | 오탐 방지용 임계값 |
| 키보드 감지 | `innerHeight - visualViewport.height - offsetTop > 56` 이면 open | `frontend/src/hooks/useKeyboardInset.js:3` | `DEFAULT_THRESHOLD_PX=56` | 모바일 hide-nav 정책과 연결 |

### 16-3. 하드코딩 상수/정책 값 분류

| 항목 | 값 | 위치 | 분류 | 솔직한 상태 |
|---|---|---|---|---|
| 기본 포트폴리오 현금 | `1,000,000` | `portfolio_service.py:172` | 정책 하드코딩 | 기획 기본값, 환경변수화 안됨 |
| 체결 수수료율 | `0.015%` | `portfolio_service.py:26` | 도메인 상수 | 시장/브로커별 분기 없음 |
| 슬리피지 기준치 | `6 bps` | `portfolio_service.py:27` | 휴리스틱 하드코딩 | 백테스트 기반 튜닝 미완 |
| 참여율 cap | `12%` | `portfolio_service.py:28` | 휴리스틱 하드코딩 | 종목별 차등 없음 |
| 상/하한 근접 임계 | `±28.5%` | `portfolio_service.py:30` | 휴리스틱 하드코딩 | 한국시장 30% 근접 가정 |
| 공매도 차입비용 | `8 bps/day` | `portfolio_service.py:31` | 휴리스틱 하드코딩 | 실제 대차 비용 연동 아님 |
| 레버리지 상한 | `2.0x` | `portfolio_service.py:32` | 정책 하드코딩 | MVP 제한값 |
| 라우팅 confidence | `0.7` | `config.py:49` | 정책 하드코딩 | 운영 중 재튜닝 필요 가능 |
| 라우팅 fallback 문구 | 고정 문자열 | `tutor.py:173`, `tutor.py:450` | 운영 fallback | 안전 동작 우선, 문구 정교화 여지 있음 |
| 홈 총자산 fallback | `12,450,000` | `Home.jsx:65` | 임시 UI fallback | **목업 성격 강함 (실데이터 없을 때만)** |
| 대화카드 fallback 2개 | 고정 제목 2개 | `Home.jsx:497` | 임시 UI fallback | **목업 성격 강함** |
| 캔버스 fallback 액션 | 모드별 2개 고정 문구 | `composeCanvasState.js:69` | 임시 UX fallback | LLM/서버 액션 없을 때 대체 |
| Dock dev glow 기본값 | `alpha 0.34 / blur 28 / spread 0.22` | `AgentDock.jsx:29` | 개발 튜닝 상수 | DEV 전용, 운영 영향 없음 |
| 링크체크 제한 | `max_checks=6`, `timeout=2.4s` | `investment_intel.py:370` | 성능 보호 하드코딩 | 느린 링크에서 false 가능 |
| DART 사업보고서 코드 | `11011` | `investment_intel.py:261` | 도메인 상수 | 분기보고서/반기보고서 선택 미지원 |

### 16-4. 목업/임시 구현 여부 (솔직 공개)

| 대상 | 현재 상태 | 근거 |
|---|---|---|
| 홈 총자산 `12450000` fallback | **임시/목업 성격 있음** | 실포트폴리오/요약 값이 모두 비어있을 때만 사용 (`Home.jsx:65`) |
| 홈 대화 정리 fallback 카드 2개 | **임시/목업 성격 있음** | 세션이 없을 때 고정 문구로 카드 UI 유지 (`Home.jsx:497`) |
| 캔버스 fallback 액션 버튼 | **임시/목업 성격 있음** | `uiActions/structured` 부재 시 고정 액션 노출 (`composeCanvasState.js:176`) |
| 라우트 실패 시 inline 안내 문구 | **운영 fallback(의도적)** | 라우팅 실패시 자동 캔버스 강제 대신 안내 (`tutor.py:450`) |
| guardrail parse/API 실패 fail-open | **의도적 안전 설계** | 서비스 중단 대신 소프트 가드레일 유지 (`guardrail.py:104`, `guardrail.py:217`) |
| DART 수치 수집 연도 = 전년도 고정 | **도메인 가정(임시 아님)** | `bsns_year = now.year - 1` (`investment_intel.py:260`) |
| 캐러셀/스와이프 임계값 | **UX 튜닝 상수** | 데이터 기반 실험값이 아니라 경험값 (`Home.jsx:23`, `AgentCanvasPage.jsx:15`) |

### 16-5. 리스크와 대체 계획
- 우선순위 P0:
  - `Home` 총자산 fallback(`12450000`) 제거 또는 명시 배지 처리
  - 대화카드 fallback를 "샘플" 라벨링하거나 실제 최근 대화 없으면 빈상태 UX로 교체
- 우선순위 P1:
  - 체결 상수(슬리피지/참여율/근접패널티)를 설정 테이블/환경설정으로 외부화
  - DART `report_code`를 질의 유형에 따라 선택 가능하도록 확장
- 우선순위 P2:
  - 링크 reachability 검사 재시도/백오프 추가
  - 캐러셀/스와이프 threshold를 AB 실험값으로 치환

### 16-6. 검증 상태(정직 기록)
- 완료:
  - 코드 레벨 정적 감사(상수/분기/공식 위치 식별)
  - 문서화(계산식/하드코딩/목업 분리)
- 미완:
  - 상수 민감도 시뮬레이션(체결 모델 파라미터 튜닝 실험)
  - 실서비스 로그 기반 threshold 재튜닝
  - fallback 제거 후 UX 회귀 검증

## 17. v7.1 안정화 배치 (에러 우선 + UI 정리)

### 17-1. 문제 재현
- `POST /api/v1/learning/progress` 호출 시 간헐적이 아닌 상시 500 발생.
- 증상: `KeyError: 'id'`로 업서트 후 응답 생성 단계에서 예외.
- 사용자 체감: 캔버스/교육 플로우 중 저장 또는 진도 업데이트 순간 `internal server error`.
- 동시 관찰: 스트리밍 응답은 백엔드에서 오지만 프론트에서 델타 반영 타이밍이 흔들리며 “생성됐는데 화면에 늦게 보임/유실처럼 보임” 체감 발생.

### 17-2. 원인 분석
- 직접 원인(백엔드):
  - 파일: `fastapi/app/api/routes/learning.py`
  - 로직: `INSERT ... ON CONFLICT ... RETURNING(LearningProgress)` 결과를 `row["id"]` 방식으로 가정.
  - 실제: SQLAlchemy 반환 shape가 실행 경로에 따라 ORM 객체/row mapping으로 달라져 `id` key가 보장되지 않음.
- 체감 이슈(프론트):
  - 파일: `frontend/src/contexts/TutorChatContext.jsx`
  - SSE 파싱에서 `event:`/`data.type` 혼재 시 텍스트 델타 판정이 느슨했고, 종료 이벤트 수신 여부와 무관하게 마지막 동기화가 중복 수행될 수 있어 렌더 체감 불안정.

### 17-3. 수정 내용
- 백엔드 500 복구
  - 파일: `fastapi/app/api/routes/learning.py`
  - 변경:
    - `returning(LearningProgress.id)`로 고정.
    - 반환 ID 기준으로 `select(LearningProgress)` 재조회 후 응답 생성.
  - 효과:
    - 반환 shape 차이에 영향받지 않는 안정 경로 확보.

- 스트리밍/렌더 안정화
  - 파일: `frontend/src/contexts/TutorChatContext.jsx`
  - 변경:
    - `data:` 파싱을 공백 유무와 무관하게 처리(`data:`/`data: ` 모두 허용).
    - 이벤트 타입 정규화 우선순위 명시(`data.type` 우선, 없으면 `event:` fallback).
    - 텍스트 누적은 `text_delta` 계열 이벤트에만 반영하도록 제한.
    - `done` 수신 시 플래그 처리 후 종료 동기화 중복 실행 방지.
    - flush 주기 소폭 단축(240ms -> 180ms)으로 체감 반응성 개선.

- 홈 대화 정리 카드 단순화(제목 중심)
  - 파일: `frontend/src/pages/Home.jsx`
  - 변경:
    - snippet/키워드칩/상세 상태 텍스트 제거.
    - 제목 + 저장상태만 유지.

- 오늘의 이슈 좌우 화살표 스타일 정리
  - 파일: `frontend/src/pages/Home.jsx`
  - 변경:
    - 반투명 블러 버튼 제거.
    - 불투명 화살표 버튼(아이콘 중심)으로 교체.

- Dock 시각 개선
  - 파일: `frontend/src/components/agent/AgentDock.jsx`
  - 파일: `frontend/src/components/agent/AgentControlPulse.jsx`
  - 파일: `frontend/src/styles/globals.css`
  - 변경:
    - Dock stroke/ring 제거.
    - 상하 방향 글로우 강도 상향.
    - 본체 하단 좌측에 주황 원 + 흰 스파클(정적) 배치.
    - 상태줄 점은 pulse 애니메이션(`agent-status-dot-pulse`) 적용.
    - DEV glow tuner 패널/버튼을 기본 UI에서 제거.

- 상단바 통일
  - 파일: `frontend/src/pages/Portfolio.jsx`
  - 변경:
    - `AppHeader` -> `DashboardHeader`로 통일.

- 캔버스 헤더 버튼 줄바꿈 방지
  - 파일: `frontend/src/pages/AgentCanvasPage.jsx`
  - 변경:
    - `저장/다시 생성/중단` 버튼 그룹 `nowrap + flex-shrink-0` 적용.

### 17-4. 사용자 체감 변화
- 저장/복습 관련 500 오류가 사라지고 진도 저장이 정상 응답으로 복귀.
- 스트리밍 본문이 중간부터 더 빠르게 보이고, 완료 직전 텍스트 유실 체감 감소.
- 홈 대화 정리는 “제목만” 보이는 심플 카드로 변경.
- 오늘의 이슈 화살표가 카드 위에 과하게 떠보이지 않고 단순 컨트롤로 정리.
- Dock는 더 선명한 주황 존재감을 가지되, 스파클은 과도한 애니메이션 없이 정적 포인트로 유지.
- Portfolio/Education/Home 헤더 시각 일관성 확보.

### 17-5. API 영향
- 공개 API Breaking change 없음.
- 경로/스키마는 유지.
- 내부적으로 `learning/progress` 응답 생성 경로만 안정화(필드 shape 동일).

### 17-6. DB/운영 체크리스트 (팀 내부)
- 배포 전
  - `alembic current`가 배포 대상 revision head인지 확인.
  - `learning/progress` smoke 요청 준비(인증 포함).
  - 롤백 포인트(revision id) 명시.
- 배포 직후
  - `POST /api/v1/learning/progress` 3회 이상 반복 호출 200 확인.
  - `tutor_sessions`, `portfolio_*` 조회 경로 500 여부 확인.
  - 최근 에러로그 50건 샘플링 후 `UndefinedColumnError`, `KeyError('id')` 재발 여부 확인.
- 운영 중
  - 진도 저장 성공률/실패율 모니터링.
  - 캔버스 응답 누락 제보율(고객 피드백) 추적.
  - SSE done 미수신 비율/평균 first-delta latency 관찰.

### 17-7. 확인만 수행한 항목 (기능 확장 없음)
- 공매도/레버리지/ETF 노출 판정
  - 백엔드:
    - `position_side`, `leverage` 계산 경로 존재(지원됨).
  - 프론트 매수 UI(`TradeModal`):
    - 현재 `long 1x` 중심 입력만 노출.
    - `position_side/leverage` 직접 선택 UI는 미노출.
  - 판정:
    - "엔진은 지원, 사용자 매수 모달 노출은 미지원" 상태.
    - 후속 배치에서 UX 노출 설계 필요.

### 17-8. 솔직한 상태
- 운영 가능한 수준:
  - learning/progress 500 복구, 스트리밍 렌더 안정화, 핵심 UI 불일치 정리.
- 아직 남은 리스크:
  - 네트워크 지연/대형 응답에서 SSE 체감 편차 가능.
  - 공매도/레버리지는 백엔드 대비 프론트 노출 불균형.
