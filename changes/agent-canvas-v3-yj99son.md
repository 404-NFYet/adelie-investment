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
