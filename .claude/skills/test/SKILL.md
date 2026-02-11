---
name: test
description: 테스트 실행
user_invocable: true
---

# Test Skill

프로젝트 테스트를 실행합니다.

## 사용법

`/test $ARGUMENTS`

- `/test unit` — 유닛 테스트: `pytest tests/unit/ -v`
- `/test backend` — 백엔드 API 테스트: `pytest tests/backend/ -v`
- `/test integration` — 통합 테스트: `pytest tests/integration/ -v`
- `/test e2e` — Playwright E2E 테스트: `make test-e2e`
- `/test all` — 전체 테스트: `pytest tests/ -v`
- `/test {파일경로}` — 특정 파일: `pytest {파일경로} -v`
- `/test` (인자 없음) — Docker 기반 유닛 테스트: `make test`

## 범위별 명령 매핑

| 범위 | 명령 |
|------|------|
| `unit` | `pytest tests/unit/ -v` |
| `backend` | `pytest tests/backend/ -v` |
| `integration` | `pytest tests/integration/ -v` |
| `e2e` | `make test-e2e` |
| `load` | `make test-load` |
| `all` | `pytest tests/ -v` |
| `docker` | `make test` (docker-compose.test.yml) |

## 주의사항

- 로컬 pytest 실행 시 `.venv` 활성화 필요
- asyncio_mode = auto 설정 (pytest.ini)
- E2E 테스트는 dev 서버 실행 상태에서 수행
- 실패 시 `-x` 플래그로 첫 실패에서 중단: `pytest tests/ -v -x`
