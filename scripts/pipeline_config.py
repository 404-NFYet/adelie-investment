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
