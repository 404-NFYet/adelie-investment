# DB 운영 가이드

## 1. DB 환경 구조

| 환경 | 호스트 | 포트 | 용도 |
|------|--------|------|------|
| 공유 dev DB | `infra-server` (10.10.10.10) | 5432 | 팀 공유 개발 |
| 로컬 Docker DB | `localhost` | 5433 | 개인 격리 테스트 (`make dev`) |
| 프로덕션 DB | `deploy-test` 내부 | — | 서비스 운영 (직접 접근 금지) |

**기본 권장**: 공유 dev DB(`10.10.10.10:5432`)를 사용한다. 마이그레이션 테스트나 파괴적 작업이 필요한 경우에만 로컬 Docker DB를 사용한다.

---

## 2. .env DATABASE_URL 설정

`.env` 파일의 `DATABASE_URL`을 아래와 같이 설정한다.

**공유 dev DB 사용 시 (기본)**
```
DATABASE_URL=postgresql+asyncpg://narative:password@10.10.10.10:5432/narrative_invest
```

**로컬 Docker DB 사용 시** (`make dev` 후)
```
DATABASE_URL=postgresql+asyncpg://narative:password@localhost:5433/narrative_invest
```

> `.env` 파일은 프로젝트 루트에 위치한다. 예시: `.env.example` 참고.

---

## 3. Alembic 마이그레이션 협업 규칙

### 작성 전 필수 공지

새 마이그레이션을 작성하기 전에 반드시 **`#migration` 채널**에 공지한다.
동시에 여러 명이 마이그레이션을 작성하면 `head` revision 충돌이 발생한다.
→ **1명씩 순차 작성 원칙**을 지킨다.

### 마이그레이션 적용 방법

**로컬 venv (공유 dev DB 또는 로컬 DB)**
```bash
cd database
../.venv/bin/alembic upgrade head
```

**Docker Compose dev 환경 (로컬 DB)**
```bash
docker compose -f docker-compose.dev.yml run db-migrate
```

**deploy-test 원격 적용 (프로덕션)**
```bash
ssh deploy-test 'docker exec adelie-backend-api sh -c "cd /app/database && alembic upgrade head"'
```

**staging 원격 적용**
```bash
ssh staging 'docker exec staging-backend-api sh -c "cd /app/database && alembic upgrade head"'
```

### 현재 HEAD 확인
```bash
cd database && ../.venv/bin/alembic current
cd database && ../.venv/bin/alembic history --verbose
```

### head revision 충돌 해결

두 명이 동시에 마이그레이션을 작성해 충돌이 발생한 경우:
```bash
cd database
../.venv/bin/alembic merge heads -m "merge_conflict_resolution"
../.venv/bin/alembic upgrade head
```
머지 후 `#migration` 채널에 결과를 공유한다.

---

## 4. 콘텐츠 데이터 동기화 (prod → dev)

프로덕션 DB의 콘텐츠 데이터를 infra-server dev DB에 동기화한다.

### 동기화 실행

```bash
# 프로젝트 루트에서
make sync-dev-data
```

또는 직접 스크립트 실행:
```bash
bash database/scripts/sync_dev_data.sh
# 특정 DB 지정 시:
bash database/scripts/sync_dev_data.sh postgresql://narative:password@localhost:5433/narrative_invest
```

### 동기화 대상 테이블 (7개)

| 테이블 | 설명 |
|--------|------|
| `stock_listings` | 종목 목록 |
| `daily_briefings` | 일별 브리핑 |
| `briefing_stocks` | 브리핑-종목 연결 |
| `historical_cases` | 과거 사례 |
| `case_matches` | 사례 매칭 |
| `case_stock_relations` | 사례-종목 관계 |
| `broker_reports` | 증권사 리포트 |

> 스키마 테이블(`users`, `portfolios` 등 유저 데이터)은 동기화하지 않는다.

### 주의사항

- **스키마 선행 적용 필수**: 동기화 전 대상 DB에 `alembic upgrade head`가 완료되어야 한다.
- `deploy-test` SSH 접속이 가능한 환경에서만 실행 가능하다.
- `psql` 클라이언트 설치 필요: `sudo apt install postgresql-client`
- 동기화는 기존 데이터를 `TRUNCATE CASCADE` 후 재삽입하므로 대상 DB의 콘텐츠 데이터가 초기화된다.
- 실행 주기: 주요 파이프라인 실행 후 또는 팀 요청 시 인프라 담당자가 실행한다.

---

## 5. 원격 DB 직접 접속

### infra-server dev DB (개발 시 참조)
```bash
psql -h 10.10.10.10 -p 5432 -U narative -d narrative_invest
```

### deploy-test prod DB (읽기 전용 조회만 허용)
```bash
# SSH를 통해 접속
ssh deploy-test "docker exec -it adelie-postgres psql -U narative -d narrative_invest"
```

> 프로덕션 DB에 직접 `INSERT`/`UPDATE`/`DELETE`는 절대 금지한다.
> 마이그레이션은 반드시 `alembic` 을 통해서만 수행한다.

### SSH 터널링 (infra-server 포트가 외부 비노출인 경우)
```bash
ssh -L 15432:localhost:5432 infra-server -N &
# 이후 DATABASE_URL 호스트를 localhost:15432로 변경
```
