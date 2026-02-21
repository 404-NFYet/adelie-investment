# Agent Canvas v3 변경 기록 (feat/agent-canvas-v3-yj99son)

## 1. 작업 목적
- Figma 기준 홈/에이전트 캔버스 전환
- 홈 화면을 `399:2293 -> 399:3661` 흐름으로 구성
- 입력/추천문구 진입 시 `399:2765` 스타일 캔버스 화면 전환
- 기존 ChatFAB 및 버블형 채팅 중심 UX 제거

## 2. 화면 매핑
- 홈 개요: `399:2293`
  - 오렌지 자산 카드
  - 학습 스케줄 카드
  - 오늘의 이슈 카드 상단 구조
- 홈 집중: `399:3661`
  - 오늘의 이슈 + 오늘의 미션 카드 배치
  - 하단 입력바 고정 노출
- 캔버스 전환: `399:2765`
  - 상단 타이틀/상태
  - KEY POINT 카드
  - 설명/불릿/인용
  - 하단 액션 버튼 + 입력바

## 3. 파일별 변경 사항

### 3-1) 라우팅/앱 셸
- `frontend/src/App.jsx`
  - `ChatFAB` 제거
  - `AgentDock` 전역 삽입
  - `/agent` 라우트 추가 (`AgentCanvasPage`)

### 3-2) 하단 탭
- `frontend/src/components/layout/BottomNav.jsx`
  - 탭 구조: `홈(/home) / 투자(/portfolio) / MY(/profile)`
  - `/agent` 진입 시 투자 탭 active 처리
  - 바텀탭은 `/agent`에서도 유지

### 3-3) 홈 재설계
- `frontend/src/pages/Home.jsx`
  - 섹션 재배치: 자산 카드 -> 학습 스케줄 -> 오늘의 이슈 -> 오늘의 미션
  - 기존 카드뉴스 리스트 중심 구조 제거
  - 홈 컨텍스트를 `sessionStorage(adelie_home_context)`로 저장
  - 이슈 카드 CTA/칩 클릭 시 `/agent`로 전환

### 3-4) 투자 탭 에이전트 진입점
- `frontend/src/components/trading/StockDetail.jsx`
  - `이 종목 물어보기` CTA 추가
  - `onAskAgent` prop 추가
- `frontend/src/pages/Portfolio.jsx`
  - 종목 컨텍스트(`stock_code`, `stock_name`, 보유 정보) 구성
  - `/agent`로 state 전달

### 3-5) 신규 Agent UI
- `frontend/src/components/agent/AgentDock.jsx` (신규)
  - 하단 고정 입력바
  - 추천문구를 placeholder 스타일로 반투명 표시
  - 경로/모드별 프롬프트 전환
- `frontend/src/pages/AgentCanvasPage.jsx` (신규)
  - 캔버스형 응답 화면
  - `useTutor`의 SSE/세션 재사용
  - `context_text` 전달용 `setContextInfo(stepContent)` 적용
- `frontend/src/components/agent/AgentCanvasSections.jsx` (신규)
  - 캔버스 섹션 렌더링 (Key Point/설명/불릿/액션)

### 3-6) 신규 훅/유틸
- `frontend/src/hooks/useAgentPromptHints.js` (신규)
  - 페이지별 모드/placeholder/추천문구 결정
- `frontend/src/utils/agent/composeCanvasState.js` (신규)
  - SSE assistant 텍스트를 캔버스 표시 모델로 변환
  - `keyPoint`, `explanation`, `bullets`, `quote`, `actions` 도출

### 3-7) 제거 파일
- `frontend/src/components/layout/ChatFAB.jsx` 삭제

## 4. 데이터/백엔드 영향
- 파이프라인 변경 없음
- DB 스키마 변경 없음
- FastAPI 엔드포인트 변경 없음
- `/api/v1/tutor/chat` 재사용

## 5. 프론트 내부 인터페이스 확장
- `context_text` 전달 형식
  - `setContextInfo({ type, id, stepContent })`의 `stepContent`에 JSON 문자열 주입
  - 홈 모드: 이슈 요약/키워드 정보
  - 종목 모드: 종목 및 보유 정보

## 6. QA 체크리스트
- [ ] 홈 진입 시 상단 자산/학습/이슈 섹션 레이아웃 확인
- [ ] 오늘의 미션 카드 표시 및 클릭 동작 확인
- [ ] 하단 입력바가 홈/투자/MY/agent에서 지속 노출 확인
- [ ] 입력바 placeholder가 페이지별로 변경되는지 확인
- [ ] 입력/CTA로 `/agent` 전환되는지 확인
- [ ] 캔버스 화면에서 버블 채팅 없이 요약/불릿/액션 표시 확인
- [ ] 종목 상세 `이 종목 물어보기` 컨텍스트 반영 확인
- [ ] 뒤로가기 시 이전 화면 복귀 및 하단탭 유지 확인
- [ ] 모바일/데스크톱에서 하단 입력바 + 바텀탭 겹침 확인

## 7. 리스크/후속
- 기존 용어 하이라이트(튜터 모달) 경로는 레거시로 유지됨
- 캔버스 텍스트 파싱 품질은 LLM 출력 형식에 영향받음
- 후속 개선 항목
  - action 버튼별 구조화 프롬프트
  - depth(3단계) 정책을 서버/클라이언트 공통 규칙으로 고정
  - 홈/종목별 컨텍스트 스키마 정교화
