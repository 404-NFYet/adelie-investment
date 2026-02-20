# Adelie News Lab

기존 앱 코드 수정 없이 동작하는 독립 뉴스 분석 앱입니다.

## 기능
- KR/US 유명 매체 RSS 헤드라인 조회
- 기사 URL 직접 입력 분석
- Figma 기준 모바일 뉴스 피드/상세 화면 구성
- 결과 모드 2종
  - 원문+해설
  - 한눈요약 (배경/중요성/개념/관련/핵심정리)
- 하이라이트 용어 클릭 설명
- 분석 직후 자동 차트 생성 + 재시도

## 구조
- `backend`: FastAPI sidecar (`/api/news/*`)
- `frontend`: React + Vite

## 로컬 실행

### 1) 백엔드
```bash
cd news_lab/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8091
```

### 2) 프론트
```bash
cd news_lab/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3011
```

브라우저: `http://localhost:3011`

## Docker Compose 실행
```bash
cd news_lab
docker compose -f docker-compose.news.yml up --build
```

## 환경변수
- `OPENAI_API_KEY`: 설정 시 LLM 요약 활성화
- `UPSTREAM_API_BASE`: 기존 백엔드 API base (기본 `http://host.docker.internal:8082/api/v1`)
- `REDIS_URL`: 선택 (없으면 메모리 캐시)

## 테스트
```bash
cd news_lab/backend
PYTHONPATH=. pytest -q
```
