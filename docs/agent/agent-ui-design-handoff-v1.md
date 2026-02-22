# Agent UI Design Handoff v1

## 1) 목적
- 프론트 구현 담당 에이전트가 동일한 톤/밀도로 화면을 구현할 수 있도록 공통 UI 가이드를 제공한다.
- 범위: `AgentDock`, `AgentCanvasPage`, `Home 대화 정리 카드`, `Education 복습 카드`.

## 2) 공통 토큰
- 기본 배경: `#F7F8FA`
- 카드 배경: `#FFFFFF`
- 보더: `#E8EBED`
- 그림자: `0 1px 4px rgba(0,0,0,0.04)` / 강조 `0 2px 8px rgba(0,0,0,0.06)`
- 텍스트:
  - 제목 `#191F28`
  - 본문 `#4E5968`
  - 보조 `#8B95A1`
- 포인트 컬러: `#FF6B00` (CTA/active에서만 사용)
- Radius:
  - small: `14px`
  - medium: `18px`
  - large card: `20~24px`

## 3) 하단 영역 레이아웃 규칙
- 하단 고정 요소는 `BottomNav + AgentDock` 2단 구성.
- 본문 페이지는 다음 패딩을 공통 적용:
  - `pb-[calc(var(--bottom-nav-h)+var(--agent-dock-h)+16px)]`
- Dock 높이 기준:
  - `--agent-dock-h: 104px` (세션 복귀 바 포함 최대치 기준)

## 4) AgentDock 명세
- 입력창 우측 아이콘 순서:
  - `검색 토글(지구본)` → `기록(시계)` → `전송`
- 검색 토글:
  - ON: `#FFF2E8` 배경, 아이콘 `#FF6B00`
  - OFF: `#F2F4F6` 배경, 아이콘 `#8B95A1`
- 기록 버튼:
  - 항상 노출
  - 탭 시 `/agent/history`
- 세션 복귀 바:
  - 높이 최소화(`py-1.5`)
  - 문구 1줄 + 우측 chevron

## 5) Canvas 명세
- 상단 헤더는 1줄 고정:
  - `뒤로가기`, `타이틀`, `상태점`, `정보`, `기록`
- 본문:
  - markdown 렌더 우선
  - 구조화 요약은 보조 카드로 표시
- 스와이프 힌트:
  - 핸들 + `n/m` + 짧은 토스트
  - 문장형 장문 안내는 금지

## 6) Home 명세 (대화 정리)
- “오늘의 이슈” 아이콘:
  - `issueCard.icon_key` 기반 렌더
  - fallback: `DEFAULT_HOME_ICON_KEY`
- 기존 미션 카드 레이아웃 재사용
- 데이터 소스만 최근 세션 요약으로 교체:
  - `title`, `last_message_at`, `message_count`

## 7) Education 명세 (복습 카드)
- 카드 소스:
  - `learning_progress` + 로컬 메타(`review_meta:*`)
- CTA:
  - `복습 완료` 버튼
  - 완료 상태는 회색 배지 처리
- 콘텐츠 진입:
  - `case` → narrative
  - `briefing` → agent canvas 복습 프롬프트

## 8) 구현 체크리스트
- [ ] Dock 아이콘 3종(추천/검색/기록/전송) 간 간격 균일
- [ ] 본문-하단 겹침 없음(홈/투자/교육/agent/history)
- [ ] 오늘의 이슈 아이콘이 `icon_key`로 표시
- [ ] Canvas markdown 렌더(헤딩/리스트/강조/수식) 정상
- [ ] 복습 카드 완료 액션 반영 후 상태 즉시 변경
