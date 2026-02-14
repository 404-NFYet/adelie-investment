# 팀 미팅 — 2026년 2월 14일

> 소요 시간: 약 40분
> 참석자: 손영진, 정지훈, 안례진, 허진서, 도형준

---

## 안건 1. 역할 재편 확인 (5분)

새 역할 배정과 각 팀원의 담당 범위를 확인합니다.

| 이름 | 새 역할 | 브랜치 | LXD 인스턴스 |
|------|---------|--------|-------------|
| 손영진 | PM / Frontend | dev/frontend | dev-yj99son |
| 정지훈 | Chatbot | dev/chatbot | dev-j2hoon10 |
| 안례진 | Data Pipeline | dev/pipeline | dev-ryejinn |
| 허진서 | Backend (FastAPI, DB) | dev/backend | dev-jjjh02 |
| 도형준 | Infra (Docker, CI/CD) | dev/infra | dev-hj |

**참고:**
- 각 역할의 상세 담당 디렉토리는 안건 4에서 설명
- Git user.name / user.email은 기존과 동일하게 유지

---

## 안건 2. 새 브랜치 전략 (5분)

### 브랜치 구조

```
prod          ← 프로덕션 배포 (보호됨)
 └── develop  ← 통합 브랜치 (PR만 가능)
      ├── dev/frontend   (손영진)
      ├── dev/chatbot    (정지훈)
      ├── dev/pipeline   (안례진)
      ├── dev/backend    (허진서)
      └── dev/infra      (도형준)
```

### 브랜치 역할

| 브랜치 | 용도 | 비고 |
|--------|------|------|
| `main` | 소개 페이지 전용 | 코드 없음, README만 유지 |
| `develop` | 통합 브랜치 | 모든 dev/* 브랜치의 머지 대상 |
| `prod` | 프로덕션 배포 | develop에서 릴리스 PR로 머지 |
| `dev/{part}` | 파트별 개발 | 각 담당자가 자유롭게 커밋 |

### PR 워크플로우

1. **dev/{part} -> develop**: 기능 완성 시 PR 생성 -> 최소 1명 리뷰 -> 머지
2. **develop -> prod**: 릴리스 준비 완료 시 릴리스 PR -> 팀 리뷰 -> 머지 후 배포

---

## 안건 3. 개발 환경 사용법 (10분)

### SSH 접속

```bash
# 호스트 SSH config에 아래 설정 추가 필요
# Host dev-{name}
#     HostName 10.10.10.{번호}
#     User ubuntu

ssh dev-yj99son      # 손영진
ssh dev-j2hoon10     # 정지훈
ssh dev-ryejinn      # 안례진
ssh dev-jjjh02       # 허진서
ssh dev-hj           # 도형준
```

### 프론트엔드 개발

```bash
cd ~/adelie-investment/frontend
npm install
npm run dev
# http://localhost:3001 (또는 LXD 컨테이너 IP:3001)
```

### 백엔드 개발

```bash
cd ~/adelie-investment
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload
# 또는
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload
```

### Docker 개발 환경

```bash
cd ~/adelie-investment
docker compose -f docker-compose.dev.yml up
# PostgreSQL: localhost:5433
# Redis: localhost:6379
# Frontend: localhost:3001
# Backend API: localhost:8082
```

---

## 안건 4. 파트별 담당 범위 + 교차 의존성 (10분)

### 담당 디렉토리

| 파트 | 주 담당 디렉토리 | 보조 참조 |
|------|----------------|----------|
| Frontend | `frontend/` | `fastapi/app/schemas/` (API 스키마) |
| Chatbot | `chatbot/` | `fastapi/app/services/tutor_engine.py` |
| Pipeline | `datapipeline/` | `database/alembic/` (스키마 변경 시) |
| Backend | `fastapi/`, `database/` | `chatbot/` (import 연동) |
| Infra | `lxd/`, `docker-compose.*.yml`, `.github/` | 전체 Dockerfile |

### CODEOWNERS

CODEOWNERS 파일을 통해 PR 자동 리뷰어 지정:
- `frontend/` 변경 -> 손영진 자동 리뷰 요청
- `fastapi/` 변경 -> 허진서 자동 리뷰 요청
- 등등 (파트별 동일 패턴)

### 교차 의존성 핵심

**API 스키마 변경 시 프론트/백엔드 동기화가 필수:**

1. Backend에서 `app/schemas/`의 Pydantic 모델 변경
2. Frontend의 `src/api/` 호출 코드 동시 업데이트 필요
3. 스키마 변경이 포함된 PR에는 반드시 프론트엔드 담당자 리뷰 포함

**기타 교차 의존성:**
- DB 스키마 변경 -> Alembic 마이그레이션 + Backend 모델 + Pipeline writer 동시 수정
- 챗봇 도구 추가 -> Backend 라우트 추가 가능성 있음

---

## 안건 5. Docker/Git 규칙 (5분)

### 커밋 메시지 형식

```
type: 한글 설명
```

**type 종류:** `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `style`, `perf`

**예시:**
```
feat: 키워드 카드 즐겨찾기 기능 추가
fix: 로그인 토큰 만료 시 리다이렉트 오류 수정
chore: docker-compose.dev.yml Redis 버전 업데이트
```

### Docker 태깅 규칙

| 태그 | 용도 | 예시 |
|------|------|------|
| `latest` | 최신 stable 이미지 | `dorae222/adelie-frontend:latest` |
| `v{M.m.p}` | 릴리스 버전 | `dorae222/adelie-frontend:v1.2.0` |
| `dev-{SHA}` | 개발 빌드 | `dorae222/adelie-frontend:dev-abc1234` |

### 환경변수 관리

- `.env` 파일은 git에 포함하지 않음 (.gitignore)
- 새 팀원 또는 새 컨테이너 세팅 시 기존 팀원에게 `.env` 파일 전달
- API 키 공유: 팀 내부 보안 채널(DM 등)로만 전달, 절대 커밋/PR에 포함 금지

---

## 안건 6. Q&A (5분)

자유 질의응답.

---

## Action Items

- [ ] **각 팀원**: dev 컨테이너 SSH 접속 확인 (`ssh dev-{name}`)
- [ ] **각 팀원**: dev/{part} 브랜치 확인 (`git branch -a`)
- [ ] **각 팀원**: `.env` 파일 API 키 설정 (OPENAI, PERPLEXITY, LANGCHAIN 등)
- [ ] **각 팀원**: `npm run dev` 프론트엔드 동작 확인
- [ ] **인프라(도형준)**: LXD 프로파일 적용 (dev-ryejinn 승격)
- [ ] **인프라(도형준)**: GitHub default branch -> develop 변경, branch protection 설정
- [ ] **PM(손영진)**: main 브랜치 README 업데이트 확인
