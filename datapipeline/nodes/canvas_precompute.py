"""Canvas 사전 연산 노드 — datapipeline 완료 후 Canvas 초기 분석 캐싱.

save_to_db 이후 실행되어, 당일 브리핑 결과를 기반으로
Canvas 초기 화면용 분석을 사전 연산하여 Redis에 저장합니다.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))


async def canvas_precompute_node(state: dict) -> dict:
    """Canvas home 모드 사전 연산.

    파이프라인에서 생성된 브리핑 데이터를 기반으로
    Canvas 초기 분석 + CTA를 사전 생성하여 Redis에 캐싱합니다.

    state 필요 키:
        - full_output: 조립된 최종 브리핑 JSON
        - db_result: DB 저장 결과 (briefing_id 등)
    """
    if state.get("error"):
        return {"error": state["error"]}

    logger.info("[Node] canvas_precompute — Canvas 사전 연산 시작")

    full_output = state.get("full_output")
    if not full_output or not isinstance(full_output, dict):
        logger.warning("canvas_precompute: full_output 없음, 건너뜀")
        return {"metrics": {"canvas_precompute": "skipped_no_output"}}

    try:
        # 브리핑 요약 추출
        theme = full_output.get("theme", "")
        one_liner = full_output.get("one_liner", "")
        pages = full_output.get("pages", [])

        # 키워드별 요약 수집
        summaries = []
        for page in pages[:5]:
            if isinstance(page, dict):
                title = page.get("title", "")
                purpose = page.get("page_purpose", {})
                if isinstance(purpose, dict):
                    summary_text = purpose.get("summary", "")
                else:
                    summary_text = str(purpose)[:300]
                if title:
                    summaries.append(f"### {title}\n{summary_text}")

        # 분석 마크다운 조립
        analysis_parts = []
        if theme:
            analysis_parts.append(f"## {theme}")
        if one_liner:
            analysis_parts.append(f"*{one_liner}*")
        if summaries:
            analysis_parts.append("\n\n".join(summaries))

        analysis_md = "\n\n".join(analysis_parts) if analysis_parts else None

        if not analysis_md:
            logger.info("canvas_precompute: 분석 마크다운 생성 실패, 건너뜀")
            return {"metrics": {"canvas_precompute": "skipped_empty_analysis"}}

        # CTA 생성
        ctas = [
            {
                "id": "portfolio_impact",
                "label": "내 포트에 영향",
                "type": "prompt",
                "prompt": f"오늘 '{theme}' 이슈가 내 포트폴리오에 미치는 영향을 분석해줘",
            },
            {
                "id": "risk_analysis",
                "label": "리스크 분석",
                "type": "prompt",
                "prompt": f"'{theme}' 관련 주요 리스크 요인을 분석해줘",
            },
            {
                "id": "historical_compare",
                "label": "과거 사례 비교",
                "type": "prompt",
                "prompt": "비슷한 과거 시장 상황과 비교 분석해줘",
            },
        ]

        # 소스 수집
        sources = full_output.get("sources", [])
        if not isinstance(sources, list):
            sources = []

        # Redis 저장
        from datapipeline.config import REDIS_URL
        import redis.asyncio as aioredis

        today = datetime.now(KST).strftime("%Y-%m-%d")
        cache_key = f"canvas:precompute:home:{today}"

        payload = {
            "analysis_md": analysis_md,
            "ctas": ctas,
            "chart_json": None,  # 차트는 full_output의 charts에서 추출 가능
            "sources": sources[:10],
            "generated_at": datetime.now(KST).isoformat(),
        }

        try:
            r = aioredis.from_url(REDIS_URL, decode_responses=True)
            await r.set(cache_key, json.dumps(payload, ensure_ascii=False), ex=86400)
            await r.aclose()
            logger.info("canvas_precompute: Redis 저장 완료 [%s]", cache_key)
        except Exception as e:
            logger.warning("canvas_precompute: Redis 저장 실패: %s", e)
            return {"metrics": {"canvas_precompute": f"redis_error: {e}"}}

        return {"metrics": {"canvas_precompute": "success"}}

    except Exception as e:
        logger.exception("canvas_precompute 노드 에러: %s", e)
        # 사전 연산 실패는 파이프라인 전체를 실패시키지 않음
        return {"metrics": {"canvas_precompute": f"error: {e}"}}
