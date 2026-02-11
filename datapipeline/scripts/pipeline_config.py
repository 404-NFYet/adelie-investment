"""파이프라인 공통 설정 상수.

keyword_pipeline_graph.py, generate_cases.py에서 공유하는
매직넘버와 설정값을 한 곳에서 관리.
"""

# ── 종목 선별 ──
TOP_CANDIDATES = 30          # 기술지표 계산 대상 종목 수
TRENDING_TARGET = 15         # 트렌드 선별 수
THEME_TARGET = 5             # 테마 클러스터 수
FINAL_KEYWORDS = 3           # 최종 키워드 수
MIN_TRENDING = 5             # 최소 트렌딩 종목 (미달 시 에러)

# ── API ──
API_TIMEOUT = 30             # LLM/Perplexity 타임아웃 (초)
MAX_RETRIES = 3              # API 재시도 횟수
RETRY_BASE_DELAY = 2         # 재시도 기본 대기 (초)

# ── 품질 점수 ──
SECTOR_ANALYSIS_BONUS = 5    # 섹터 분석 존재 시 보너스
MACRO_CONTEXT_BONUS = 5      # 매크로 분석 존재 시 보너스
SECTOR_ROTATION_BONUS = 10   # 섹터 로테이션 부합 시 보너스
FALLBACK_QUALITY_SCORE = 50  # 폴백 키워드 기본 점수
ANALYSIS_TRUNCATION = 500    # 섹터/매크로 분석 텍스트 최대 길이

# ── Perplexity 검색 도메인 ──
KOREAN_FINANCIAL_DOMAINS = [
    "naver.com",
    "hankyung.com",
    "chosun.com",
    "mk.co.kr",
    "sedaily.com",
    "bloter.net",
    "etnews.com",
    "thebell.co.kr",
]

# ── 콘텐츠 품질 기준 (골든케이스 수준) ──
MIN_CONTENT_LENGTH = 150       # content 최소 글자 수
MIN_BULLETS = 3                # bullets 최소 개수
MIN_GLOSSARY = 1               # 페이지당 glossary 최소 개수
MIN_UNIQUE_CHART_TYPES = 3     # 6페이지에서 최소 고유 차트 유형 수

# ── KOSPI/KOSDAQ 필터링 ──
MIN_TRADE_VALUE = 500_000_000  # 최소 거래대금 5억원/일

# ── 6페이지 골든케이스 ──
PAGE_KEYS = ["background", "concept_explain", "history", "application", "caution", "summary"]
PAGE_TITLES = {
    "background": "현재 배경",
    "concept_explain": "금융 개념 설명",
    "history": "과거 비슷한 사례",
    "application": "현재 상황에 적용",
    "caution": "주의해야 할 점",
    "summary": "최종 정리",
}
GOLDEN_COLORS = ["#FF6B35", "#004E89", "#1A936F", "#C5D86D", "#8B95A1", "#FF6B00"]
