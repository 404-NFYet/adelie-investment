# 파이프라인 개발 가이드 — 안례진

## 환경 정보
- LXD 컨테이너: `ssh dev-ryejinn`
- Git 설정: user.name=ryejinn, user.email=arj1018@ewhain.net
- 브랜치: `dev/pipeline`

## 개발 시작

### Docker 환경 (권장)
```bash
# Mock 모드 (LLM 호출 없이 테스트 데이터 생성)
docker compose --profile pipeline run ai-pipeline \
  python -m datapipeline.run --backend mock --market KR

# Live 모드 (실제 LLM 호출, 크롤링, DB 저장)
docker compose --profile pipeline run ai-pipeline \
  python -m datapipeline.run --backend live --market KR
```
- Mock 모드: API 키 불필요, 빠른 테스트용
- Live 모드: `.env`에서 `OPENAI_API_KEY`, `PERPLEXITY_API_KEY` 필요

### 로컬 환경 (Docker 없이)
```bash
source .venv/bin/activate

# Mock 모드
.venv/bin/python -m datapipeline.run --backend mock

# Live 모드 (원격 DB 접속 가능)
.venv/bin/python -m datapipeline.run --backend live --market KR
```
- `.env`의 `DATABASE_URL` 확인 (로컬 또는 원격 DB)
- 프로젝트 루트에서 실행

## 담당 디렉토리

```
datapipeline/
├── graph.py                     # LangGraph StateGraph 정의 (18노드)
├── run.py                       # 파이프라인 실행 진입점
├── config.py                    # 환경변수 기반 설정, KST 유틸
├── schemas.py                   # Pydantic 상태 스키마
├── nodes/                       # LangGraph 노드 함수
│   ├── crawlers.py              # 뉴스/리서치 크롤링 노드
│   ├── screening.py             # 종목 스크리닝 노드
│   ├── curation.py              # OpenAI 큐레이션 노드
│   ├── interface1.py            # 1차 질문 생성 (Perplexity)
│   ├── interface2.py            # 역사적 사례 검색 (Perplexity)
│   ├── interface3.py            # 최종 내러티브 생성 (OpenAI)
│   ├── db_save.py               # DB 저장 노드 (asyncpg)
│   └── ...
├── data_collection/             # 데이터 수집 모듈
│   ├── news_crawler.py          # 뉴스 크롤러
│   ├── research_crawler.py      # 리서치 리포트 크롤러
│   ├── screener.py              # 종목 스크리닝
│   ├── openai_curator.py        # OpenAI 큐레이터
│   └── ...
├── ai/                          # LLM 클라이언트
│   ├── multi_provider_client.py # OpenAI, Perplexity, Claude 통합
│   └── llm_utils.py             # 프롬프트 로딩, 재시도 로직
├── db/
│   └── writer.py                # asyncpg 직접 DB 저장
├── prompts/templates/           # 마크다운 프롬프트 (frontmatter)
│   ├── page_purpose.md          # 1차 질문 생성
│   ├── historical_case.md       # 역사적 사례 검색
│   ├── narrative_body.md        # 내러티브 본문 생성
│   ├── hallucination_check.md   # 환각 검증
│   ├── final_hallucination.md   # 최종 환각 검증
│   ├── chart_generation.md      # 차트 생성
│   ├── glossary_generation.md   # 용어집 생성
│   ├── _chart_skeletons.md      # 차트 스켈레톤
│   └── _tone_guide.md           # 톤 가이드
├── collectors/                  # 레거시 pykrx 수집기 (FastAPI 호환)
└── scripts/                     # 레거시 파이프라인 스크립트
    ├── seed_fresh_data_integrated.py
    └── generate_cases.py
```

### 핵심 파일
- `graph.py`: 18노드 LangGraph, StateGraph 정의, 노드 간 엣지
- `run.py`: `--backend [mock|live]`, `--market [KR|US]` 옵션 처리
- `config.py`: `kst_today()`, `PROJECT_ROOT`, 환경변수 로드
- `ai/multi_provider_client.py`: OpenAI, Perplexity, Claude 통합 인터페이스
- `prompts/templates/*.md`: frontmatter (provider, model, temperature, thinking)

## 개발 워크플로우

1. **새 노드 추가**
   ```python
   # nodes/new_node.py
   from datapipeline.schemas import PipelineState

   async def new_node(state: PipelineState) -> dict:
       # 노드 로직
       return {"new_field": value}

   # graph.py에 노드 등록
   graph.add_node("new_node", new_node)
   graph.add_edge("previous_node", "new_node")
   ```

2. **프롬프트 수정**
   - `prompts/templates/` 내 .md 파일 편집
   - frontmatter에서 provider, model, temperature 설정
   - `ai/llm_utils.py`의 `load_prompt()`가 자동 로드

3. **Mock 데이터 추가**
   - Mock 모드에서 사용할 테스트 데이터는 각 노드에서 직접 생성
   - 예: `nodes/crawlers.py`에서 `backend == "mock"` 분기 처리

4. **DB 저장 로직 수정**
   ```python
   # db/writer.py
   async def save_narrative(conn, narrative_data):
       await conn.execute(
           "INSERT INTO narratives (...) VALUES (...)",
           narrative_data
       )
   ```
   - DB 스키마 변경 시 Backend 팀(허진서)과 협업 필요

## 테스트

### Unit 테스트
```bash
pytest datapipeline/tests/ -v

# 로컬 실행
source .venv/bin/activate
pytest datapipeline/tests/test_nodes.py -v
pytest datapipeline/tests/test_ai_client.py::test_openai -v
```

### 통합 테스트 (Mock 모드)
```bash
# 전체 파이프라인 실행 (LLM 호출 없이)
docker compose --profile pipeline run ai-pipeline \
  python -m datapipeline.run --backend mock
```
- 성공 시 18노드 모두 통과, DB에 테스트 데이터 저장됨

### Live 모드 검증
```bash
# 실제 LLM 호출 + 크롤링
docker compose --profile pipeline run ai-pipeline \
  python -m datapipeline.run --backend live --market KR
```
- `.env`에 API 키 필요
- 생성된 내러티브 품질 수동 검증 (DB 또는 Frontend에서 확인)

## 다른 파트와의 연동

### Backend (허진서)
- **영향받는 경우**: DB 스키마 변경 (keywords, cases, narratives, glossary 등)
- **대응**:
  - Alembic migration 확인
  - `db/writer.py` 쿼리 수정
  - `schemas.py` Pydantic 모델 업데이트
- **주의**:
  - SQLAlchemy 모델과 asyncpg 쿼리 일치 확인
  - KST 날짜 처리 (`config.py`의 `kst_today()` 사용)

### Frontend (손영진)
- **영향주는 경우**: narrative 구조 변경, glossary 포맷 변경
- **알림 필요**:
  - narrative JSON 구조 변경 → `pages/CasePage.jsx` 수정
  - glossary 포맷 변경 → `components/domain/GlossaryTooltip.jsx` 수정
- **주의**: DB에 저장된 데이터가 Frontend UI와 일치해야 함

### Chatbot (정지훈)
- **영향주는 경우**: glossary 구조 변경, narrative 포맷 변경
- **알림 필요**:
  - `glossary_tool.py` 쿼리 로직 수정 필요 여부
  - 튜터가 참조하는 데이터 스키마 변경 시 알림
- **주의**: Pipeline 출력 → 튜터 입력 데이터 일관성

### Infra (도형준)
- **영향받는 경우**: Docker 이미지 재빌드, API 키 추가, 스케줄링 설정
- **협업 필요**:
  - `.env.example`에 `OPENAI_API_KEY`, `PERPLEXITY_API_KEY` 추가
  - `docker-compose.prod.yml`에 cron 스케줄 설정
  - deploy-test 배포 시 파이프라인 실행 확인
- **주의**:
  - Live 모드 실행 시간 (약 10~20분 소요)
  - DB 저장 실패 시 롤백 로직 확인

## 프롬프트 품질 관리

### 프롬프트 변경 후 검증 절차
1. Mock 모드로 파이프라인 실행 → 구조적 오류 확인
2. Live 모드로 소량 데이터 실행 → LLM 응답 품질 확인
3. LangSmith 추적 로그 확인 (토큰 사용량, 레이턴시)
4. 생성된 내러티브 수동 검증 (환각, 톤, 정확도)

### 환각 검증 프롬프트 튜닝
- `prompts/templates/hallucination_check.md` 수정
- `prompts/templates/final_hallucination.md`에서 최종 검증
- 환각 감지 시 노드에서 재시도 또는 필터링 로직 추가

## 커밋 전 체크리스트
- [ ] `git config user.name` = ryejinn
- [ ] `git config user.email` = arj1018@ewhain.net
- [ ] Mock 모드 테스트 통과 (`--backend mock`)
- [ ] Live 모드 샘플 실행 후 내러티브 품질 확인
- [ ] 프롬프트 변경 시 출력 포맷 일관성 검증
- [ ] DB 스키마 변경 시 Backend 팀과 마이그레이션 확인
- [ ] 커밋 메시지 형식: `feat: 역사적 사례 검색 프롬프트 개선` (한글, type prefix)
