# Cobrowse Protocol v0

## REST (초안)
### 1) 세션 생성
- `POST /api/v1/agent/cobrowse/sessions`
- request
```json
{
  "context_route": "/home",
  "mode": "home"
}
```
- response
```json
{
  "session_id": "uuid",
  "host_token": "jwt",
  "join_token": "short-code",
  "expires_at": "ISO8601"
}
```

### 2) 세션 참가
- `POST /api/v1/agent/cobrowse/sessions/{session_id}/join`
- request
```json
{
  "join_token": "short-code",
  "role": "guest"
}
```

### 3) 세션 종료
- `POST /api/v1/agent/cobrowse/sessions/{session_id}/close`

## WebSocket 이벤트 (초안)
채널: `/ws/agent/cobrowse/{session_id}`

### 공통 envelope
```json
{
  "type": "event_type",
  "session_id": "uuid",
  "actor": "host|guest|system",
  "timestamp": "ISO8601",
  "payload": {}
}
```

### 이벤트 타입
- `presence`: 입장/퇴장 상태
- `state_sync`: route, visible_sections, selected_entities, scroll, focus
- `control_request`: guest가 제어 요청
- `control_approved`: host 승인
- `control_rejected`: host 거절
- `control_result`: 실행 성공/실패
- `heartbeat`: 연결 유지

## 고위험 액션 규칙
- `risk=high`는 항상 `control_request -> control_approved` 이후 실행
- 승인 타임아웃 기본 10초
- 타임아웃/거절 시 `control_rejected` + 이유 포함

## 보안 요구사항
- host/guest 토큰 서명 검증
- 세션별 권한 격리
- 이벤트 감사 로그(요청/승인/실행 결과) 저장
