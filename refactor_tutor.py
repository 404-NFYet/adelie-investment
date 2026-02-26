import os

tutor_path = "fastapi/app/api/routes/tutor.py"
with open(tutor_path, "r", encoding="utf-8") as f:
    content = f.read()

# I am going to find pieces of code and move them

# 1. extract page_context block
start_page_ctx = content.find("    # 컨텍스트 주입 (사용자가 보고 있는 페이지 기반)")
end_page_ctx = content.find("    # 포트폴리오 컨텍스트 주입", start_page_ctx)
page_ctx_code = content[start_page_ctx:end_page_ctx]

# 2. extract portfolio block
start_portfolio = end_page_ctx
end_portfolio = content.find("    # 출처 수집", start_portfolio)
portfolio_code = content[start_portfolio:end_portfolio]

# 3. extract sources block
start_sources = end_portfolio
end_sources = content.find("    # --- V5 Prompt Caching", start_sources)
sources_code = content[start_sources:end_sources]

# 4. extract prev_msgs block
start_prev_msgs = content.find("    # 3. 과거 대화 내역 (매 턴마다 변경됨)")
end_prev_msgs = content.find("    # 4. 최종 메시지 배열 조립", start_prev_msgs)
prev_msgs_code = content[start_prev_msgs:end_prev_msgs]

# 5. extract guardrail block
start_guardrail = content.find("    # 가드레일 검사")
end_guardrail = content.find("    api_key = get_settings().OPENAI_API_KEY")
guardrail_code = content[start_guardrail:end_guardrail]

# I will replace the guardrail block with the moved blocks + the new guardrail call
new_guardrail_logic = f"""{page_ctx_code}
{portfolio_code}
{sources_code}
{prev_msgs_code}
    # 가드레일용 문맥 조립
    guardrail_context = page_context
    last_assistant_msgs = [m["content"] for m in prev_msgs if m["role"] == "assistant"]
    if last_assistant_msgs:
        guardrail_context += f"\\n\\n[직전 챗봇의 답변]\\n{{last_assistant_msgs[-1]}}"

    # 가드레일 검사
    try:
        guardrail_result = await run_guardrail(request.message, context=guardrail_context)
        if not guardrail_result.is_allowed:
            # 차단 메시지를 스트리밍으로 전송
            yield f"event: text_delta\\ndata: {{json.dumps({{'content': guardrail_result.block_message}})}}\\n\\n"
            # 차단되어도 대화 흐름을 유지할 수 있도록 DB 세션/메시지 저장 처리
            try:
                from datetime import datetime
                from app.models.tutor import TutorSession, TutorMessage
                
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

            yield f"event: done\\ndata: {{json.dumps({{'session_id': session_id, 'total_tokens': 0, 'guardrail': guardrail_result.decision}})}}\\n\\n"
            return
    except Exception as e:
        logger.warning(f"Guardrail check failed, falling open: {{e}}")

"""

# Now we construct the final string by removing the old blocks
new_content = content.replace(guardrail_code, new_guardrail_logic)
new_content = new_content.replace(page_ctx_code, "")
new_content = new_content.replace(portfolio_code, "")
new_content = new_content.replace(sources_code, "")
new_content = new_content.replace(prev_msgs_code, "")

with open(tutor_path, "w", encoding="utf-8") as f:
    f.write(new_content)
