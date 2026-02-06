"""
# [2026-02-06] 단어 하이라이팅 서비스
AI 생성 콘텐츠 내 어려운 용어를 자동 식별하고 마킹하는 서비스.
사용자 난이도 설정에 따라 하이라이팅할 용어를 결정.
"""

import re
from typing import Optional

# 난이도별 하이라이팅 대상 용어
# beginner: 모든 전문용어 하이라이팅
# elementary: 중급 이상 용어만 하이라이팅
# intermediate: 고급 용어만 하이라이팅

TERMS_BY_DIFFICULTY = {
    "beginner": [
        # 기본 지표
        "PER", "PBR", "EPS", "ROE", "ROA", "PSR", "PCR",
        # 시장 용어
        "시가총액", "거래량", "시가", "종가", "고가", "저가",
        "배당", "배당금", "배당수익률", "배당성향",
        # 투자 용어
        "분산투자", "포트폴리오", "리밸런싱", "손절", "익절",
        "매수", "매도", "호가", "지정가", "시장가",
        # 금융상품
        "ETF", "펀드", "채권", "국채", "회사채",
        # 기업 용어
        "영업이익", "순이익", "매출액", "부채비율", "자본",
        "자산", "유동자산", "고정자산", "자기자본",
    ],
    "elementary": [
        # 심화 지표
        "EBITDA", "EV/EBITDA", "PEG", "BPS", "DPS",
        # 기술적 분석
        "이동평균선", "볼린저밴드", "RSI", "MACD", "스토캐스틱",
        "지지선", "저항선", "추세선", "골든크로스", "데드크로스",
        # 재무 용어
        "영업현금흐름", "잉여현금흐름", "감가상각", "상각",
        "자본적지출", "운전자본", "레버리지",
        # 거시경제
        "금리", "기준금리", "인플레이션", "디플레이션",
        "양적완화", "테이퍼링", "환율", "원달러환율",
    ],
    "intermediate": [
        # 고급 분석
        "베타", "알파", "샤프비율", "변동성",
        "VaR", "CVaR", "상관계수", "공분산",
        # 파생상품
        "선물", "옵션", "콜옵션", "풋옵션", "내재가치", "시간가치",
        "델타", "감마", "세타", "베가",
        # M&A
        "인수합병", "기업가치", "신주발행", "자사주매입",
        "유상증자", "무상증자", "액면분할", "액면병합",
    ],
}


def get_terms_for_difficulty(user_difficulty: str) -> list[str]:
    """사용자 난이도에 따라 하이라이팅할 용어 목록 반환."""
    all_terms = []
    
    if user_difficulty == "beginner":
        all_terms.extend(TERMS_BY_DIFFICULTY["beginner"])
        all_terms.extend(TERMS_BY_DIFFICULTY["elementary"])
        all_terms.extend(TERMS_BY_DIFFICULTY["intermediate"])
    elif user_difficulty == "elementary":
        all_terms.extend(TERMS_BY_DIFFICULTY["elementary"])
        all_terms.extend(TERMS_BY_DIFFICULTY["intermediate"])
    else:  # intermediate
        all_terms.extend(TERMS_BY_DIFFICULTY["intermediate"])
    
    return all_terms


def highlight_terms_in_content(
    content: str,
    user_difficulty: str = "beginner",
    custom_terms: Optional[list[str]] = None,
) -> dict:
    """
    콘텐츠 내 어려운 용어를 [[용어]] 형식으로 마킹.
    
    Args:
        content: 원본 콘텐츠
        user_difficulty: 사용자 난이도 (beginner, elementary, intermediate)
        custom_terms: 추가로 하이라이팅할 용어 목록
    
    Returns:
        {
            "content": "마킹된 콘텐츠",
            "highlighted_terms": [{"term": "PER", "count": 2, "difficulty": "beginner"}, ...]
        }
    """
    terms = get_terms_for_difficulty(user_difficulty)
    if custom_terms:
        terms.extend(custom_terms)
    
    # 용어 길이 역순으로 정렬 (긴 용어 먼저 매칭)
    terms = sorted(set(terms), key=len, reverse=True)
    
    highlighted_content = content
    found_terms = []
    
    for term in terms:
        # 대소문자 무시 패턴
        pattern = re.compile(rf'\b({re.escape(term)})\b', re.IGNORECASE)
        matches = pattern.findall(highlighted_content)
        
        if matches:
            # 이미 마킹된 부분은 제외
            if f"[[{term}]]" not in highlighted_content:
                highlighted_content = pattern.sub(rf'[[\1]]', highlighted_content)
                
                # 해당 용어의 난이도 결정
                term_difficulty = "intermediate"
                for diff, term_list in TERMS_BY_DIFFICULTY.items():
                    if term.upper() in [t.upper() for t in term_list]:
                        term_difficulty = diff
                        break
                
                found_terms.append({
                    "term": term,
                    "count": len(matches),
                    "difficulty": term_difficulty,
                })
    
    return {
        "content": highlighted_content,
        "highlighted_terms": found_terms,
    }


def extract_terms_from_highlighted(content: str) -> list[str]:
    """마킹된 콘텐츠에서 용어 목록 추출."""
    pattern = re.compile(r'\[\[([^\]]+)\]\]')
    return list(set(pattern.findall(content)))


def remove_highlighting(content: str) -> str:
    """마킹 제거하여 원본 콘텐츠 반환."""
    pattern = re.compile(r'\[\[([^\]]+)\]\]')
    return pattern.sub(r'\1', content)
