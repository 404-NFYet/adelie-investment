"""AI 튜터 응답 생성 엔진.

SSE 스트리밍 응답 생성, 컨텍스트 수집, 자동 시각화를 담당한다.
라우트 엔드포인트와 분리하여 핵심 비즈니스 로직만 포함.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI
import time
from fastapi import Request

from app.core.config import get_settings
from app.models.tutor import TutorSession, TutorMessage
from app.models.glossary import Glossary
from app.models.historical_case import HistoricalCase
from app.models.report import BrokerReport
from app.schemas.tutor import TutorChatRequest
from app.services import get_redis_cache
from app.services.stock_resolver import (
    detect_stock_codes,
    should_auto_visualize,
    fetch_stock_data_for_context,
    get_fundamentals_text,
)
from pathlib import Path

logger = logging.getLogger("narrative.tutor_engine")


# --- 난이도별 프롬프트 ---

def get_difficulty_prompt(difficulty: str) -> str:
    """난이도별 시스템 프롬프트 반환 (md 파일에서 로드)."""
    prompts_dir = Path(__file__).parent.parent / "prompts" / "templates"
    file_map = {
        "beginner": "tutor_beginner.md",
        "elementary": "tutor_elementary.md",
        "intermediate": "tutor_intermediate.md",
    }
    
    file_name = file_map.get(difficulty, "tutor_beginner.md")
    prompt_path = prompts_dir / file_name
    
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"Failed to load prompt file {file_name}: {e}")
        return "당신은 친절한 주식 투자 튜터입니다. 쉽게 설명해주세요."



# --- 컨텍스트 수집 ---

async def _collect_glossary_context(
    message: str, db: AsyncSession
) -> tuple[str, list[dict]]:
    """메시지에서 용어를 감지하고 glossary DB를 조회하여 컨텍스트와 출처를 반환."""
    common_terms = ["PER", "PBR", "EPS", "ROE", "ROA", "ETF", "배당", "시가총액"]
    terms_to_search = [t for t in common_terms if t.lower() in message.lower()]

    glossary_context = ""
    sources = []

    for term in terms_to_search:
        result = await db.execute(
            select(Glossary).where(Glossary.term.ilike(f"%{term}%"))
        )
        item = result.scalar_one_or_none()
        if item:
            glossary_context += f"\n{item.term}: {item.definition_short}"
            sources.append({
                "type": "glossary",
                "title": item.term,
                "content": item.definition_short or "",
                "url": f"/api/v1/glossary/{item.id}",
            })

    return glossary_context, sources


async def _collect_db_context(
    message: str, db: AsyncSession
) -> tuple[str, list[dict]]:
    """DB에서 사례/리포트를 검색하여 컨텍스트와 출처를 반환."""
    db_context = ""
    sources = []

    # 사례 검색
    try:
        case_result = await db.execute(
            select(HistoricalCase)
            .where(HistoricalCase.summary.ilike(f"%{message[:30]}%"))
            .order_by(HistoricalCase.created_at.desc())
            .limit(2)
        )
        for case in case_result.scalars():
            db_context += f"\n[사례] {case.title} ({case.event_year}년): {(case.summary or '')[:150]}"
            if case.source_urls:
                urls = case.source_urls if isinstance(case.source_urls, list) else []
                for url in urls[:2]:
                    if isinstance(url, str):
                        stype = "dart" if "dart" in url.lower() else "news"
                        sources.append({"type": stype, "title": "DART 공시" if stype == "dart" else "뉴스 기사", "url": url})
            sources.append({"type": "case", "title": case.title, "content": f"{case.event_year}년 — {(case.summary or '')[:80]}", "url": f"/narrative?caseId={case.id}"})
    except Exception as e:
        logger.debug("사례 검색 실패: %s", e)

    # 리포트 검색
    try:
        report_result = await db.execute(
            select(BrokerReport)
            .where(BrokerReport.report_title.ilike(f"%{message[:20]}%"))
            .order_by(BrokerReport.report_date.desc())
            .limit(2)
        )
        for report in report_result.scalars():
            db_context += f"\n[리포트] {report.broker_name}: {report.report_title} ({report.report_date})"
            sources.append({
                "type": "report",
                "title": f"{report.broker_name} — {report.report_title}",
                "content": f"{report.report_date}",
                "url": report.pdf_url or "",
            })
    except Exception as e:
        logger.debug("리포트 검색 실패: %s", e)

    return db_context, sources


async def _collect_stock_context(
    message: str, detected_stocks: list[tuple[str, str]], db: AsyncSession
) -> tuple[str, dict, list[dict]]:
    """종목 관련 데이터(주가, 기업관계, 재무지표)를 수집."""
    db_context = ""
    chart_data = {}
    sources = []

    if not detected_stocks:
        return db_context, chart_data, sources

    # pykrx 주가 조회
    stock_context, chart_data = fetch_stock_data_for_context(detected_stocks)
    if stock_context:
        db_context += stock_context
        for name, code in detected_stocks:
            sources.append({
                "type": "stock_price",
                "title": f"{name}({code}) 주가 데이터",
                "content": "pykrx 실시간 조회",
                "url": f"https://finance.naver.com/item/main.nhn?code={code}",
            })

    # 재무 지표
    for _, code in detected_stocks[:2]:
        fdr_text = get_fundamentals_text(code)
        if fdr_text:
            db_context += f"\n{fdr_text}"
            sources.append({
                "type": "financial",
                "title": f"재무 지표 ({code})",
                "content": fdr_text[:80],
                "url": f"https://finance.naver.com/item/coinfo.naver?code={code}",
            })

    return db_context, chart_data, sources


# --- 자동 시각화 (레거시 파이썬 기반 제거됨) ---

async def _auto_generate_chart(
    chart_data: dict, session_id: str, session_db_id: int, db: AsyncSession
) -> str | None:
    """자동 시각화는 백엔드 tutor 라우터 내 JSON 추출 기능으로 대체되었습니다."""
    return None


# --- 메인 응답 생성기 ---
from fastapi import Request
import time

async def generate_tutor_response_stream(
    request: TutorChatRequest,
    db: AsyncSession,
    http_request: Request,
    current_user: dict | None = None,
) -> AsyncGenerator[str, None]:
    """AI 튜터 스트리밍 응답을 생성한다 (Chart-First Architecture)."""
    
    session_id = request.session_id or str(uuid.uuid4())
    
    yield f"event: step\ndata: {json.dumps({'type': 'thinking', 'content': '질문을 분석하고 있습니다...'})}\n\n"
    
    api_key = get_settings().OPENAI_API_KEY
    if not api_key:
        yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': 'OpenAI API key not configured'})}\n\n"
        return
        
    page_context = ""
    if hasattr(request, "context_text") and request.context_text:
        page_context = (
            "\n\n[현재 학습/화면 문맥]\n"
            "사용자는 지금 애플리케이션 화면에서 아래의 내용을 직접 읽고 있는 중입니다:\n"
            f'"""\n{request.context_text}\n"""\n'
            "사용자가 질문을 할 때, 만약 사용자가 '이 화면', '방금 내용', '이 파트'와 같이 "
            "주어를 생략하더라도 반드시 위 문맥과 연관지어 자연스럽게 답변하세요."
        )
    elif request.context_type and request.context_id:
        try:
            if request.context_type == "briefing":
                ctx_result = await db.execute(text(
                    "SELECT market_summary, top_keywords FROM daily_briefings WHERE id = :id"
                ), {"id": request.context_id})
                ctx_row = ctx_result.fetchone()
                if ctx_row:
                    page_context = f"\n\n[현재 보고 있는 브리핑]\n시장 요약: {ctx_row[0]}\n키워드: {ctx_row[1]}"
            elif request.context_type == "case":
                ctx_result = await db.execute(text(
                    "SELECT title, summary FROM historical_cases WHERE id = :id"
                ), {"id": request.context_id})
                ctx_row = ctx_result.fetchone()
                if ctx_row:
                    page_context = f"\n\n[현재 보고 있는 사례]\n제목: {ctx_row[0]}\n요약: {ctx_row[1]}"
        except Exception:
            pass
            
    # 포트폴리오 컨텍스트 주입 (개인화된 조언용)
    user_id = current_user["id"] if current_user else None
    if user_id:
        try:
            portfolio_result = await db.execute(text(
                "SELECT current_cash, initial_cash FROM user_portfolios WHERE user_id = :uid LIMIT 1"
            ), {"uid": user_id})
            pf_row = portfolio_result.fetchone()
            if pf_row:
                holdings_result = await db.execute(text(
                    "SELECT stock_name, quantity, avg_buy_price FROM portfolio_holdings WHERE portfolio_id = (SELECT id FROM user_portfolios WHERE user_id = :uid LIMIT 1)"
                ), {"uid": user_id})
                holdings = holdings_result.fetchall()
                holdings_text = ", ".join(f"{h[0]} {h[1]}주(평균 {int(h[2]):,}원)" for h in holdings) if holdings else "없음"
                page_context += f"\n\n[사용자 포트폴리오]\n보유 현금: {int(pf_row[0]):,}원 / 초기 자본: {int(pf_row[1]):,}원\n보유 종목: {holdings_text}"
        except Exception:
            pass

    # 출처 수집 (glossary, DB 사례/리포트, 주가/기업관계)
    sources = []
    extra_context = ""
    try:
        glossary_context, glossary_sources = await _collect_glossary_context(request.message, db)
        db_context, db_sources = await _collect_db_context(request.message, db)
        detected_stocks = detect_stock_codes(request.message)
        stock_context, chart_data, stock_sources = await _collect_stock_context(
            request.message, detected_stocks, db
        )
        sources = glossary_sources + db_sources + stock_sources
        if glossary_context:
            extra_context += f"\n\n참고할 용어 정의:{glossary_context}"
        if db_context:
            extra_context += f"\n\n참고할 내부 데이터:{db_context}"
        if stock_context:
            extra_context += f"\n\n참고할 종목 데이터:{stock_context}"
    except Exception as e:
        logger.warning("출처 수집 실패 (무시): %s", e)
        detected_stocks = []
        chart_data = {}

    # 과거 대화 내역 조립
    prev_msgs = []
    if request.session_id:
        try:
            existing_session = await db.execute(
                select(TutorSession).where(TutorSession.session_uuid == uuid.UUID(request.session_id))
            )
            session_obj = existing_session.scalar_one_or_none()
            if session_obj:
                prev_result = await db.execute(
                    select(TutorMessage)
                    .where(TutorMessage.session_id == session_obj.id)
                    .order_by(TutorMessage.created_at)
                    .limit(20)
                )
                for msg in prev_result.scalars():
                    prev_msgs.append({"role": msg.role, "content": msg.content})
        except Exception as e:
            logger.warning("Failed to load previous messages: %s", e)

    # 가드레일용 문맥 조립
    from chatbot.services.guardrail import run_guardrail
    guardrail_context = page_context
    last_assistant_msgs = [m["content"] for m in prev_msgs if m["role"] == "assistant"]
    if last_assistant_msgs:
        guardrail_context += f"\n\n[직전 챗봇의 답변]\n{last_assistant_msgs[-1]}"

    # 가드레일 검사
    try:
        guardrail_result = await run_guardrail(request.message, context=guardrail_context)
        if not guardrail_result.is_allowed:
            yield f"event: text_delta\ndata: {json.dumps({'content': guardrail_result.block_message})}\n\n"
            
            try:
                session_obj = None
                if request.session_id:
                    existing = await db.execute(
                        select(TutorSession).where(TutorSession.session_uuid == uuid.UUID(request.session_id))
                    )
                    session_obj = existing.scalar_one_or_none()

                if not session_obj:
                    user_id = current_user["id"] if current_user else None
                    session_obj = TutorSession(
                        session_uuid=uuid.UUID(session_id),
                        user_id=user_id,
                        context_type=request.context_type,
                        context_id=request.context_id,
                        title=request.message[:50],
                        message_count=0,
                    )
                    db.add(session_obj)
                    await db.flush()

                user_msg = TutorMessage(
                    session_id=session_obj.id,
                    role="user",
                    content=request.message,
                    message_type="text",
                )
                db.add(user_msg)

                assistant_msg = TutorMessage(
                    session_id=session_obj.id,
                    role="assistant",
                    content=guardrail_result.block_message,
                    message_type="text",
                )
                db.add(assistant_msg)

                session_obj.message_count = (session_obj.message_count or 0) + 2
                session_obj.last_message_at = datetime.utcnow()
                await db.commit()
            except Exception as e:
                logger.warning("가드레일 차단 내역 DB 저장 실패: %s", e)

            yield f"event: done\ndata: {json.dumps({'session_id': session_id, 'total_tokens': 0, 'guardrail': guardrail_result.decision})}\n\n"
            return
    except Exception as e:
        logger.warning(f"Guardrail check failed, falling open: {e}")

    dynamic_context = page_context + extra_context
    
    # -------------------------------------------------------------
    # Chart-First Architecture 파이프라인
    # -------------------------------------------------------------
    from app.schemas.tutor import ChartType
    from chatbot.services.tutor_chart_generator import classify_chart_request, generate_chart_json
    
    user_requested_viz = should_auto_visualize(request.message, bool(detected_stocks), prev_msgs)
    should_viz = user_requested_viz or bool(chart_data)
    logger.info("[Chart-First] user_requested_viz=%s, chart_data=%s, should_viz=%s", user_requested_viz, bool(chart_data), should_viz)
    
    chart_system_prompt = ""
    fallback_msg_sent = False
    
    if should_viz:
        try:
            # 컨텍스트를 활용하여 차트 종류 판별
            viz_context = f"사용자 질문: {request.message}\n조회된 데이터: {dynamic_context[:1000]}"
            classification = await classify_chart_request(request.message, viz_context)
            logger.info("[Chart-First] classification result: chart_type=%s", classification.chart_type)
            
            if classification.chart_type == ChartType.UNSUPPORTED:
                if user_requested_viz:
                    # 차트 생성 실패 시 즉시 로딩을 대체하여 텍스트 출력
                    fallback_msg = "지금은 해당 시각화를 지원하지 않아요. 빠르게 업데이트하도록 할게요! 🐧\n\n"
                    yield f"event: text_delta\ndata: {json.dumps({'content': fallback_msg})}\n\n"
                    fallback_msg_sent = True
                    # 프롬프트 제어
                    chart_system_prompt = "[시스템 안내] 차트 시각화가 기술적으로 불가능하거나 실패했습니다. 데이터의 흐름과 수치를 텍스트만으로 최대한 상세하고 직관적으로 설명해 주세요."
            else:
                yield f"event: action\ndata: {json.dumps({'action_type': 'visualizing', 'message': '데이터 시각화 중이에요. 잠시만 기다려주세요...'})}\n\n"
                
                # 차트 JSON 렌더링
                chart_json = await generate_chart_json(viz_context, classification.chart_type)
                logger.info("[Chart-First] chart_json generated: %s", bool(chart_json))
                if chart_json and "data" in chart_json and isinstance(chart_json["data"], list):
                    for trace in chart_json["data"]:
                        if "type" not in trace:
                            trace["type"] = classification.chart_type.value
                            
                    # 이벤트 전송
                    yield f"event: visualization\ndata: {json.dumps({'type': 'visualization', 'format': 'json', 'chartData': chart_json})}\n\n"
                    
                    # 프롬프트 제어 (ASCII 방지 강력한 통제)
                    chart_system_prompt = (
                        "[[CRITICAL INSTRUCTION]]\n"
                        "이미 UI 상에 실제 대화형 인터랙티브 차트(Plotly)가 성공적으로 그려졌습니다.\n"
                        "따라서 텍스트 답변에는 '아래는 차트입니다' 같은 중복된 멘트나, 텍스트 기호(|, *, ─, _, 공백 등)를 사용해 "
                        "시각적으로 차트/그래프를 묘사하려는 시도를 **절대로** 하지 마세요. (위반 시 시스템 오류 발생 간주)\n"
                        "오직 차트에서 나타나는 수치의 변동폭, 지지선/저항선 부근의 움직임, 또는 펀더멘털과 결합된 '전문적인 줄글 해석'만을 제공하세요."
                    )
        except Exception as viz_err:
            logger.warning(f"시각화 파이프라인 실패: {viz_err}")
            chart_system_prompt = "[시스템 안내] 차트 시각화가 시스템 오류로 중단되었습니다. 수치를 텍스트만으로 유용하게 설명해 주세요."

    # -------------------------------------------------------------
    # 메인 LLM 텍스트 답변 생성 파이프라인
    # -------------------------------------------------------------
    system_base_rules = get_difficulty_prompt(request.difficulty)
    system_base_rules += (
        "\n\n[출력 형식 규칙]\n"
        "- 수식은 반드시 LaTeX로 렌더링되게 작성하세요: 인라인 $...$, 블록 $$...$$\n"
        "- 일반 텍스트는 마크다운: **볼드**, *이탤릭*, 불릿/번호 기호를 활용해 가독성을 높이세요.\n"
        "- 두 가지 이상의 상반된/비교 데이터를 설명할 때는 반드시 마크다운 테이블(| 컬럼1 | 컬럼2 |)을 사용하세요.\n"
        "- 소제목은 ## 또는 ### 를 사용하고 3줄 이상의 긴 답변은 문단 구분을 명확히 하세요.\n"
        "- 투자 용어가 나오면 괄호 안에 쉬운 설명을 덧붙여주세요. 예: PER(주가수익비율, 주가를 이익으로 나눈 값).\n"
        "\n[답변 구조 (3-Step 러닝 사이클)]\n"
        "반드시 답변 마지막 문단에는 사용자의 이해도를 묻는 '메타인지 역질문' 1개를 포함하세요.\n"
        "1. 질문에 대한 핵심 답변 (마크다운 포맷팅 적용)\n"
        "2. [자기 점검] 메타인지 역질문 (예: '방금 설명드린 개념에서 가장 이해하기 어려운 부분은 어디였나요?')"
    )

    if prev_msgs:
        system_base_rules += "\n\n[중요] 이전 대화 기록입니다. 사용자와 이미 대화 중이므로 인사를 절대로 반복하지 마세요."

    messages = [{"role": "system", "content": system_base_rules}]
    if dynamic_context:
        messages.append({"role": "system", "content": f"[참고용 동적 컨텍스트]\n{dynamic_context}"})
    if chart_system_prompt:
        messages.append({"role": "system", "content": chart_system_prompt})
        
    messages.extend(prev_msgs)
    messages.append({"role": "user", "content": request.message})
    
    try:
        import asyncio
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=4096,
            stream=True,
        )
        
        total_tokens = 0
        full_response = "지금은 해당 시각화를 지원하지 않아요. 빠르게 업데이트하도록 할게요! 🐧\n\n" if fallback_msg_sent else ""
        stream_start = time.monotonic()
        chunk_count = 0
        
        async for chunk in response:
            chunk_count += 1
            if chunk_count % 10 == 0:
                if time.monotonic() - stream_start > 300:
                    logger.warning("SSE 스트리밍 타임아웃 (300초 초과)")
                    yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': 'Stream timeout'})}\n\n"
                    break
                if await http_request.is_disconnected():
                    logger.info("클라이언트 연결 해제 감지, 스트리밍 중단")
                    break

            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield f"event: text_delta\ndata: {json.dumps({'content': content})}\n\n"
            
            if chunk.usage:
                total_tokens = chunk.usage.total_tokens
        
        # Save session & message to DB
        try:
            session_obj = None
            if request.session_id:
                existing = await db.execute(
                    select(TutorSession).where(TutorSession.session_uuid == uuid.UUID(request.session_id))
                )
                session_obj = existing.scalar_one_or_none()

            if not session_obj:
                user_id = current_user["id"] if current_user else None
                session_obj = TutorSession(
                    session_uuid=uuid.UUID(session_id),
                    user_id=user_id,
                    context_type=request.context_type,
                    context_id=request.context_id,
                    title=request.message[:50],
                    message_count=0,
                )
                db.add(session_obj)
                await db.flush()

            user_msg = TutorMessage(
                session_id=session_obj.id,
                role="user",
                content=request.message,
                message_type="text",
            )
            db.add(user_msg)

            assistant_msg = TutorMessage(
                session_id=session_obj.id,
                role="assistant",
                content=full_response,
                message_type="text",
            )
            db.add(assistant_msg)

            session_obj.message_count = (session_obj.message_count or 0) + 2
            session_obj.last_message_at = datetime.utcnow()
            await db.commit()
        except Exception as e:
            logger.warning("Failed to save tutor session: %s", e)

        done_data = {'session_id': session_id, 'total_tokens': total_tokens}
        if sources:
            done_data['type'] = 'done'
            done_data['sources'] = sources
        yield f"event: done\ndata: {json.dumps(done_data)}\n\n"
        
    except asyncio.TimeoutError:
        logger.warning("OpenAI API 호출 타임아웃")
        yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': 'AI 응답 시간 초과'})}\n\n"
    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
