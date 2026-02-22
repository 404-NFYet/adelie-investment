# Cobrowse Architecture v0

## 범위
- 이번 단계는 설계/스캐폴딩만 포함한다.
- 실시간 공동 제어 완전 구현은 다음 단계에서 진행한다.

## 목표
- 사용자와 에이전트(또는 오퍼레이터)가 동일 화면 상태를 공유한다.
- 제어 요청/승인/결과를 추적 가능한 이벤트로 관리한다.

## 역할
- `host`: 세션 소유자(사용자)
- `guest`: 보조 제어자(에이전트 또는 상담자)

## 컴포넌트
- Frontend
  - Presence 표시
  - Remote state 적용기
  - Control request 승인 UI
- Backend
  - 세션 수명 관리(생성/참여/종료)
  - 상태 동기화 브로드캐스트
  - 권한/승인 정책

## 데이터 흐름
1. host가 cobrowse 세션 생성
2. guest가 토큰으로 참가
3. host 화면 상태가 주기/이벤트 기반으로 동기화
4. guest 제어 요청 발생
5. 정책에 따라 즉시 실행 또는 host 승인
6. 결과 이벤트 브로드캐스트

## 권한 모델
- low-risk: 정책상 auto-allow 가능
- high-risk: host 승인 mandatory
- deny/timeout 시 실행 취소 이벤트 발행

## 장애 대응
- WS 단절 시 read-only 모드 전환
- 세션 토큰 만료 시 자동 종료
- 충돌 이벤트 발생 시 host 상태를 source of truth로 복구
