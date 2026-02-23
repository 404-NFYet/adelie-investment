# Phase 1: UI/UX 리팩토링

## 문제

기존 AI 튜터 화면이 전체 화면 전환 방식으로, 사용자 흐름이 끊기고 모바일 AI 채팅 UX 표준과 맞지 않았습니다.

- 좌우 스와이프 네비게이션이 불필요하게 복잡
- 채팅 말풍선 스타일 구분 없음
- 마크다운 렌더링 가독성 부족

## 해결

### 1. 팝업 채팅 시트 (`AgentChatSheet.jsx`)
- 화면 전환 대신 하단에서 85% 높이로 올라오는 시트 방식
- `framer-motion` 애니메이션 적용

### 2. 채팅 말풍선 구분 (`ChatBubble.jsx`)
- **사용자**: 주황색 배경(#FF6B00), 흰색 텍스트, 오른쪽 정렬
- **에이전트**: 흰색 배경, 검정 텍스트, 왼쪽 정렬, 펭귄 아이콘

### 3. 마크다운 렌더링 강화
- `remark-gfm`, `rehype-katex`, `remark-math` 플러그인 적용
- 제목, 불릿, 테이블, 인용문, 강조 표현 커스텀 스타일링
- 코드 블록 구문 강조

### 4. 입력 바 개선 (`AgentChatInput.jsx`)
- 라운딩 증가 (`rounded-2xl`)
- 주황색 전송 버튼
- 상태 인디케이터 표시

## 변경 파일

- `frontend/src/components/agent/AgentChatSheet.jsx` (신규)
- `frontend/src/components/agent/ChatBubble.jsx` (신규)
- `frontend/src/components/agent/AgentChatInput.jsx` (신규)
- `frontend/src/components/agent/AgentChatHeader.jsx` (신규)
- `frontend/src/App.jsx` (TutorModal → AgentChatSheet 교체)
