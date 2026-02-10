# Experiments - 데이터 파이프라인 실험 환경

이 폴더는 **로컬 테스트용** 데이터 파이프라인 실험 환경입니다.  
프로덕션 코드와 분리되어 있어 자유롭게 실험할 수 있습니다.

## 폴더 구조

```
experiments/
├── docker-compose.yml         # 로컬 테스트용 Docker 환경
├── .env.example               # 환경 변수 예시
├── Dockerfile.pipeline        # 파이프라인 컨테이너
├── requirements.txt           # Python 의존성
├── run.py                     # 파이프라인 CLI 엔트리 포인트
├── pipeline/                  # 파이프라인 코드
│   ├── config.py              # 설정 (환경 변수)
│   ├── ai_service.py          # OpenAI/Perplexity/Anthropic API 호출
│   ├── generator.py           # 파이프라인 오케스트레이터
│   ├── rss_service.py         # RSS 피드 수집
│   ├── diversity.py           # 다양성 필터 (중복 제거)
│   ├── types.py               # 타입 정의
│   ├── repository.py          # PostgreSQL 직접 접근
│   ├── prompt_loader.py       # 프롬프트 템플릿 로더
│   └── main.py                # 파이프라인 메인 실행
├── prompts/                   # 프롬프트 템플릿
│   ├── keyword_extraction.md  # 키워드 추출
│   ├── planner.md             # 스토리 플래닝
│   ├── writer.md              # 스토리 작성
│   ├── reviewer.md            # 품질 리뷰
│   ├── glossary.md            # 용어집 생성
│   ├── tone_corrector.md      # 아델리 톤 교정
│   ├── research_context.md    # 맥락 리서치
│   └── research_simulation.md # 시뮬레이션 리서치
├── collectors/                # 데이터 수집 모듈
│   ├── naver_industry.py      # 네이버 산업 리포트 크롤러
│   ├── naver_economy.py       # 네이버 경제 리포트 크롤러
│   ├── rss_collector.py       # feedparser 기반 RSS 수집기
│   └── pdf_extractor.py       # PDF 텍스트 추출기
├── notebooks/                 # Jupyter 노트북
│   └── pipeline_test.ipynb    # 파이프라인 테스트 노트북
├── naver_crawler/             # 레거시 크롤러 (참고용)
│   └── crawler.py
└── data/                      # 결과 데이터 저장소
```

## 시작하기

### 1. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일에 API 키 입력
```

### 2. 의존성 설치

```bash
# 로컬 실행
pip install -r requirements.txt

# 또는 Docker 사용
docker-compose up -d pipeline
```

### 3. 파이프라인 실행

```bash
# 전체 파이프라인
python run.py

# 개별 단계
python run.py --step keywords   # 키워드 추출만
python run.py --step research   # 리서치만
python run.py --step story      # 스토리 생성만

# 데이터 수집만
python run.py --collect rss     # RSS 뉴스 수집
python run.py --collect naver   # 네이버 리포트 수집
```

### 4. Jupyter 노트북

```bash
cd experiments
jupyter notebook notebooks/pipeline_test.ipynb
```

### 5. Docker 환경 (DB 포함)

```bash
# 파이프라인 + PostgreSQL + Redis
docker-compose --profile with-db up -d

# 파이프라인 컨테이너에서 실행
docker-compose exec pipeline python run.py
```

## 실험 예시

### 키워드 추출 테스트

```python
from pipeline.config import PipelineConfig
from pipeline.ai_service import AIPipelineService
from pipeline.rss_service import RSSService

config = PipelineConfig()
ai = AIPipelineService(config)
rss = RSSService()

news = await rss.fetch_top_news()
keywords = await ai.extract_top_keywords(news)
print([kw.keyword for kw in keywords])
```

### 네이버 리포트 수집

```python
from collectors.naver_industry import NaverIndustryCrawler
from datetime import date

crawler = NaverIndustryCrawler()
reports = await crawler.fetch_reports(date.today().strftime("%Y%m%d"))
print(f"수집된 리포트: {len(reports)}건")
await crawler.close()
```

### PDF 텍스트 추출

```python
from collectors.pdf_extractor import PDFExtractor

extractor = PDFExtractor()
result = await extractor.extract_from_url("https://example.com/report.pdf")
print(f"추출 텍스트: {result.char_count}자")
```

## 프로덕션 코드와의 차이

| 항목 | 프로덕션 (backend_api/) | 실험 (experiments/) |
|------|------------------------|-------------------|
| DB 접근 | SQLAlchemy ORM + 모델 | raw SQL 또는 JSON 파일 |
| 설정 | pydantic-settings | dataclass + dotenv |
| 의존성 | FastAPI 전체 스택 | 최소 의존성 |
| 실행 | Docker + Scheduler | CLI / Notebook |
| 결과 저장 | DB 필수 | JSON 파일 (기본), DB (선택) |

## 주의사항

- 이 폴더의 코드는 **실험용**이며, 프로덕션에 직접 반영되지 않습니다.
- API 키는 절대 커밋하지 마세요 (`.env`는 `.gitignore`에 포함).
- 대량 크롤링 시 요청 간격을 준수하세요.
- 실험 결과는 `data/` 디렉토리에 JSON으로 저장됩니다.