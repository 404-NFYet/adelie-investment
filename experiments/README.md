# Experiments - 데이터 파이프라인 실험 환경

이 폴더는 **로컬 테스트용** 데이터 파이프라인 실험 환경입니다.  
프로덕션 코드와 분리되어 있어 자유롭게 실험할 수 있습니다.

## 폴더 구조

```
experiments/
├── docker-compose.yml    # 로컬 테스트용 Docker 환경
├── .env.example          # 환경 변수 예시
├── pipeline/             # 파이프라인 코드 실험
│   └── config.py         # 파이프라인 설정
├── naver_crawler/        # 네이버 증권 크롤러 실험
│   └── crawler.py        # 크롤러 코드
└── data/                 # 임시 데이터 저장소
```

## 시작하기

### 1. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일에 API 키 입력
```

### 2. Docker 환경 실행

```bash
docker-compose up -d
```

### 3. 파이프라인 테스트

```bash
# Docker 컨테이너 내에서 실행
docker-compose exec pipeline python pipeline/run_test.py
```

## 실험 예시

### 키워드 추출 테스트

```python
from pipeline.config import PipelineConfig
from pipeline.ai_service import AIPipelineService

config = PipelineConfig()
ai = AIPipelineService(config)

# 테스트 뉴스로 키워드 추출
keywords = await ai.extract_keywords(news_text)
print(keywords)
```

### 네이버 리포트 크롤링 테스트

```python
from naver_crawler.crawler import NaverReportCrawler
from datetime import date

crawler = NaverReportCrawler()
reports = await crawler.fetch_reports_by_date(date.today())
print(f"수집된 리포트 수: {len(reports)}")
```

## 주의사항

- 이 폴더의 코드는 **실험용**이며, 프로덕션에 반영되지 않습니다.
- API 키는 절대 커밋하지 마세요 (`.env`는 `.gitignore`에 포함).
- 대량 크롤링 시 요청 간격을 준수하세요.
