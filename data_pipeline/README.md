# Narrative Investment Data Pipeline

주식 데이터 및 리서치 리포트 수집을 위한 데이터 파이프라인입니다.

## 기능

- **주식 데이터 수집**: pykrx를 사용한 급등/급락/거래량 상위 종목 수집
- **리서치 리포트 수집**: 네이버 금융 리서치 리포트 크롤링
- **PDF 처리**: GPT-4o Vision을 사용한 리포트 텍스트/표/차트 추출
- **DB 저장**: PostgreSQL에 수집 데이터 저장

## 설치

```bash
cd data-pipeline
pip install -r requirements.txt
```

## 환경 설정

`.env` 파일 설정 (상위 디렉토리):

```env
# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/narative

# OpenAI (PDF 처리용)
OPENAI_API_KEY=sk-xxx

# MinIO (선택적)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

## 사용법

### 주식 데이터 수집

```bash
# 오늘 날짜 급등/급락 종목 수집
python run_pipeline.py --collect-stocks

# 특정 날짜 수집
python run_pipeline.py --date 2026-02-05 --collect-stocks

# 상위 20개 종목 수집
python run_pipeline.py --collect-stocks --top-n 20

# DB에 저장
python run_pipeline.py --collect-stocks --save-to-db
```

### 리서치 리포트 수집

```bash
# 최신 리포트 1페이지 수집
python run_pipeline.py --collect-reports

# 3페이지 수집 + PDF 다운로드
python run_pipeline.py --collect-reports --pages 3 --download-pdf

# 특정 종목 리포트만 수집
python run_pipeline.py --collect-reports --stock-code 005930 --pages 5

# DB에 저장
python run_pipeline.py --collect-reports --save-to-db
```

### 모든 수집 실행

```bash
# 주식 + 리포트 전체 수집
python run_pipeline.py --date 2026-02-05 --all --save-to-db
```

### PDF 처리 (Vision API)

```bash
# PDF 파일 처리
python run_pipeline.py --process-pdf ./downloads/report.pdf

# 최대 5페이지만 처리
python run_pipeline.py --process-pdf ./downloads/report.pdf --max-pages 5
```

## 디렉토리 구조

```
data-pipeline/
├── collectors/
│   ├── stock_collector.py      # pykrx 주식 데이터 수집
│   └── naver_report_crawler.py # 네이버 리포트 크롤러
├── processors/
│   └── pdf_processor.py        # Vision LLM PDF 처리
├── loaders/
│   └── db_loader.py            # PostgreSQL 로더
├── downloads/                  # PDF 다운로드 디렉토리
├── run_pipeline.py             # 메인 실행 스크립트
├── requirements.txt
└── README.md
```

## API 참조

### stock_collector

```python
from collectors.stock_collector import get_top_movers, get_high_volume_stocks

# 급등/급락 종목
movers = get_top_movers("20260205", top_n=10)
# {"date": "...", "gainers": [...], "losers": [...]}

# 거래량 상위 종목
volume = get_high_volume_stocks("20260205", top_n=10)
# {"date": "...", "high_volume": [...]}
```

### naver_report_crawler

```python
from collectors.naver_report_crawler import collect_reports

# 리포트 수집
reports = await collect_reports(pages=2, download=True)
# [{"title": "...", "stock_name": "...", "broker": "...", ...}]
```

### pdf_processor

```python
from processors.pdf_processor import process_pdf

# PDF 처리 (Vision API 필요)
result = await process_pdf("report.pdf", max_pages=5)
# {"file": "...", "pages": [...], "combined_summary": "..."}
```

### db_loader

```python
from loaders.db_loader import DBLoader

async with DBLoader() as loader:
    await loader.ensure_tables()
    await loader.save_movers(movers_data, "gainer")
    await loader.save_reports(reports)
```

## 데이터베이스 스키마

### stock_daily_movers

| 컬럼 | 타입 | 설명 |
|------|------|------|
| date | DATE | 날짜 |
| ticker | VARCHAR(10) | 종목 코드 |
| name | VARCHAR(100) | 종목명 |
| close_price | NUMERIC | 종가 |
| change_pct | NUMERIC | 등락률 |
| mover_type | VARCHAR(20) | gainer/loser/high_volume |

### research_reports

| 컬럼 | 타입 | 설명 |
|------|------|------|
| stock_name | VARCHAR(100) | 종목명 |
| stock_code | VARCHAR(10) | 종목 코드 |
| title | VARCHAR(500) | 리포트 제목 |
| broker | VARCHAR(100) | 증권사 |
| report_date | DATE | 발행일 |
| pdf_url | TEXT | PDF URL |
| summary | TEXT | 요약 (Vision 추출) |

## 주의사항

- pykrx는 장중 호출 시 부하가 발생할 수 있으므로 장 마감 후 실행 권장
- 네이버 금융 크롤링 시 rate limiting 적용 (1초 대기)
- Vision API 사용 시 OPENAI_API_KEY 환경변수 필수
