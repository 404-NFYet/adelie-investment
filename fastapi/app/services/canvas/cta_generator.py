"""Canvas CTA 생성기 — 분석 결과 기반 다음 액션 추천.

분석 텍스트, 모드, 감지된 종목에 따라 2-3개의 CTA를 생성합니다.
CTA 피드백은 LangSmith에 기록되어 주간 개선 루프에 활용됩니다.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional

logger = logging.getLogger("narrative_api.canvas.cta_generator")

# LangSmith 트레이싱 (선택)
try:
    from langsmith import Client as LangSmithClient
    _ls_client: Optional[LangSmithClient] = None
    _HAS_LANGSMITH = True
except ImportError:
    _HAS_LANGSMITH = False
    _ls_client = None


# ── CTA 템플릿 정의 ──

_HOME_CTAS = [
    {
        "id": "portfolio_impact",
        "label": "내 포트에 영향",
        "type": "prompt",
        "prompt": "오늘 시장 이슈가 내 포트폴리오에 미치는 영향을 분석해줘",
        "icon": "portfolio",
    },
    {
        "id": "risk_analysis",
        "label": "리스크 분석",
        "type": "prompt",
        "prompt": "현재 시장 상황의 주요 리스크 요인을 분석해줘",
        "icon": "risk",
    },
    {
        "id": "historical_compare",
        "label": "과거 사례 비교",
        "type": "prompt",
        "prompt": "비슷한 과거 시장 상황과 비교 분석해줘",
        "icon": "history",
    },
    {
        "id": "sector_deep_dive",
        "label": "섹터 심층 분석",
        "type": "prompt",
        "prompt": "관련 섹터의 전체 동향을 심층 분석해줘",
        "icon": "sector",
    },
]

_STOCK_CTAS = [
    {
        "id": "stock_financials",
        "label": "재무 분석",
        "type": "prompt",
        "prompt": "이 종목의 핵심 재무지표를 분석해줘",
        "icon": "chart",
    },
    {
        "id": "stock_news",
        "label": "최신 뉴스",
        "type": "prompt",
        "prompt": "이 종목 관련 최신 뉴스와 시장 반응을 정리해줘",
        "icon": "news",
    },
    {
        "id": "stock_peer_compare",
        "label": "동종업계 비교",
        "type": "prompt",
        "prompt": "동종업계 주요 종목과 비교 분석해줘",
        "icon": "compare",
    },
    {
        "id": "stock_trade_signal",
        "label": "매매 시나리오",
        "type": "prompt",
        "prompt": "이 종목의 기술적 매매 시나리오를 분석해줘 (교육 목적)",
        "icon": "trade",
    },
    {
        "id": "stock_chart",
        "label": "차트 보기",
        "type": "prompt",
        "prompt": "이 종목의 최근 주가 흐름을 차트로 보여줘",
        "icon": "chart",
    },
]

_EDUCATION_CTAS = [
    {
        "id": "edu_quiz",
        "label": "퀴즈 풀기",
        "type": "action",
        "action_id": "start_quiz",
        "icon": "quiz",
    },
    {
        "id": "edu_glossary",
        "label": "용어 정리",
        "type": "prompt",
        "prompt": "이 주제와 관련된 핵심 금융 용어를 정리해줘",
        "icon": "glossary",
    },
    {
        "id": "edu_deeper",
        "label": "더 깊이 알기",
        "type": "prompt",
        "prompt": "이 주제를 더 깊이 설명해줘",
        "icon": "deep",
    },
]

_FOLLOW_UP_CTAS = [
    {
        "id": "follow_detail",
        "label": "더 자세히",
        "type": "prompt",
        "prompt": "방금 분석한 내용을 더 자세히 설명해줘",
        "icon": "detail",
    },
    {
        "id": "follow_chart",
        "label": "차트로 보기",
        "type": "prompt",
        "prompt": "방금 분석한 내용을 차트로 시각화해줘",
        "icon": "chart",
    },
]


async def generate_ctas(
    *,
    analysis_text: str,
    mode: str = "home",
    detected_stocks: Optional[list[tuple[str, str]]] = None,
    context_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    """분석 결과 기반 CTA 생성 (최대 3개).

    Args:
        analysis_text: 분석 결과 텍스트
        mode: 분석 모드 (home/stock/education)
        detected_stocks: 감지된 종목 [(name, code), ...]
        context_type: 컨텍스트 타입

    Returns:
        CTA 목록 [{id, label, type, prompt/action_id, icon}, ...]
    """
    ctas: list[dict[str, Any]] = []

    # 모드별 기본 CTA 풀
    if mode == "stock" and detected_stocks:
        pool = list(_STOCK_CTAS)
        stock_name = detected_stocks[0][0] if detected_stocks else ""
        # 종목명을 프롬프트에 주입
        for cta in pool:
            if "prompt" in cta and stock_name:
                cta = dict(cta)
                cta["prompt"] = cta["prompt"].replace("이 종목", f"{stock_name}")
            ctas.append(cta)
    elif mode == "education":
        pool = list(_EDUCATION_CTAS)
        ctas.extend(pool)
    else:
        pool = list(_HOME_CTAS)
        ctas.extend(pool)

    # 분석 텍스트 기반 필터링 (간단한 키워드 매칭)
    filtered = []
    for cta in ctas:
        cta_copy = dict(cta)
        cta_copy["cta_uuid"] = str(uuid.uuid4())[:8]
        filtered.append(cta_copy)

    # 후속 CTA 항상 추가
    for follow in _FOLLOW_UP_CTAS[:1]:
        f = dict(follow)
        f["cta_uuid"] = str(uuid.uuid4())[:8]
        filtered.append(f)

    # 최대 3개 반환
    return filtered[:3]


async def record_cta_feedback(
    *,
    session_id: str,
    turn_index: int,
    cta_id: str,
    action: str,
    time_to_click_ms: Optional[int] = None,
) -> None:
    """CTA 피드백을 LangSmith에 기록.

    Args:
        session_id: Canvas 세션 ID
        turn_index: 턴 인덱스
        cta_id: CTA ID
        action: "clicked" or "ignored"
        time_to_click_ms: 클릭까지 소요 시간 (ms)
    """
    feedback_data = {
        "session_id": session_id,
        "turn_index": turn_index,
        "cta_id": cta_id,
        "action": action,
        "time_to_click_ms": time_to_click_ms,
    }

    logger.info("CTA feedback: %s", json.dumps(feedback_data, ensure_ascii=False))

    if _HAS_LANGSMITH:
        try:
            global _ls_client
            if _ls_client is None:
                _ls_client = LangSmithClient()

            _ls_client.create_feedback(
                run_id=session_id,
                key="cta_interaction",
                score=1.0 if action == "clicked" else 0.0,
                comment=json.dumps(feedback_data, ensure_ascii=False),
            )
        except Exception as e:
            logger.warning("LangSmith CTA feedback failed: %s", e)
