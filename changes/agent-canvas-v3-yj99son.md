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
