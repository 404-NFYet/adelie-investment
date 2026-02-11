---
name: migrate
description: Alembic DB 마이그레이션 관리
user_invocable: true
---

# Migrate Skill

Alembic DB 마이그레이션을 관리합니다.

## 사용법

`/migrate $ARGUMENTS`

- `/migrate` 또는 `/migrate upgrade` — 최신 버전으로 마이그레이션: `alembic upgrade head`
- `/migrate current` — 현재 마이그레이션 상태 확인: `alembic current`
- `/migrate history` — 마이그레이션 히스토리 조회: `alembic history`
- `/migrate revision "메시지"` — 새 마이그레이션 파일 생성: `alembic revision --autogenerate -m "메시지"`
- `/migrate downgrade` — 한 단계 롤백: `alembic downgrade -1`

## 실행 환경

모든 alembic 명령은 `database/` 디렉토리에서 실행해야 합니다:

```bash
cd database && alembic upgrade head
```

## 서브커맨드 매핑

| 서브커맨드 | 명령 |
|-----------|------|
| `upgrade` (기본값) | `cd database && alembic upgrade head` |
| `current` | `cd database && alembic current` |
| `history` | `cd database && alembic history --verbose` |
| `revision "msg"` | `cd database && alembic revision --autogenerate -m "msg"` |
| `downgrade` | `cd database && alembic downgrade -1` |

## 주의사항

- DATABASE_URL이 .env에 설정되어 있어야 함
- autogenerate 사용 시 모든 모델이 `database/alembic/env.py`에 임포트되어 있는지 확인
- production DB에 downgrade 실행 전 반드시 백업
- 마이그레이션 파일은 `database/alembic/versions/`에 생성됨
