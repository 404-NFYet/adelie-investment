"""LangGraph 기반 가드레일 시스템."""

import json
import logging
from typing import TypedDict, Literal

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from app.core.config import get_settings

logger = logging.getLogger("narrative.guardrail")

from pathlib import Path
import os
import re

MAX_RETRIES = 2
PARSE_ERROR_MESSAGE = "일시적인 오류가 발생했어요. 잠시 후 다시 시도해 주세요 🙏"

# 1단계 (하드 차단) 키워드
MALICIOUS_KEYWORDS = [
    "씨발", "개새끼", "병신", "지랄", 
    "탈옥", "system prompt", "ignore previous instructions", "forget previous instructions"
]

class GuardrailState(TypedDict):
    """가드레일 상태(State) 정의."""
    message: str
    context: str
    decision: Literal["SAFE", "ADVICE", "OFF_TOPIC", "MALICIOUS", "PARSE_ERROR", "RETRY", ""]
    reasoning: str
    is_allowed: bool
    retries: int


# 가드레일 프롬프트 로드
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "templates" / "guardrail.md"
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    GUARDRAIL_SYSTEM_PROMPT = f.read()



async def classify_input(state: GuardrailState) -> GuardrailState:
    message = state["message"]
    context = state.get("context", "")
    retries = state.get("retries", 0)
    
    api_key = get_settings().OPENAI_API_KEY
    if not api_key:
        logger.warning("OpenAI API key missing for guardrail. Failing open.")
        return {"message": message, "context": context, "decision": "SAFE", "reasoning": "API Key missing", "is_allowed": True, "retries": retries}
        
    try:
        # temperature=0, max_tokens=256
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=256, api_key=api_key)
        
        prefix = "JSON 형식 오류가 발생했습니다. 반드시 JSON만 출력하세요.\n" if retries > 0 else ""
        
        user_input_with_context = message
        if context:
            user_input_with_context = f"[참고용 컨텍스트]\n{context}\n\n[사용자 입력]\n{message}"

        response = await llm.ainvoke([
            SystemMessage(content=prefix + GUARDRAIL_SYSTEM_PROMPT),
            HumanMessage(content=user_input_with_context)
        ])
        
        content = str(response.content).strip()
        
        # ```json 등 마크다운 블록 제거
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()
            
        parsed = json.loads(content)
        decision = parsed.get("decision", "OFF_TOPIC")
        reasoning = parsed.get("reasoning", "")
        
        if decision not in ["SAFE", "ADVICE", "OFF_TOPIC", "MALICIOUS"]:
            decision = "OFF_TOPIC"
            
        return {
            "message": message,
            "decision": decision,
            "reasoning": reasoning,
            "is_allowed": decision == "SAFE" or decision == "ADVICE",
            "retries": retries
        }
    except (json.JSONDecodeError, KeyError) as e:
        if retries < MAX_RETRIES:
            logger.info(f"guardrail parse failed (attempt {retries + 1}), retrying...")
            return {"message": message, "decision": "RETRY", "reasoning": str(e), "is_allowed": False, "retries": retries}
        else:
            logger.warning(f"guardrail parse failed after {MAX_RETRIES} retries")
            return {
                "message": message,
                "decision": "PARSE_ERROR",
                "reasoning": "JSON parsing failed",
                "is_allowed": False,
                "retries": retries
            }
    except Exception as e:
        logger.error(f"Guardrail API error: {e}")
        # API 장애 시 SAFE 통과 + 소프트 가이드만으로 방어 (Fail-open on API Error as per plan)
        return {
            "message": message,
            "decision": "SAFE",
            "reasoning": f"API Error: {e}",
            "is_allowed": True,
            "retries": retries
        }


def decide_route(state: GuardrailState) -> str:
    decision = state.get("decision")
    if decision == "RETRY":
        return "retry"
    return "end"


def increment_retry(state: GuardrailState) -> GuardrailState:
    return {
        "message": state["message"],
        "decision": state["decision"],
        "reasoning": state["reasoning"],
        "is_allowed": state.get("is_allowed", False),
        "retries": state.get("retries", 0) + 1
    }


# LangGraph 그래프 구성
workflow = StateGraph(GuardrailState)
workflow.add_node("classify_input", classify_input)
workflow.add_node("increment_retry", increment_retry)

workflow.set_entry_point("classify_input")
workflow.add_conditional_edges(
    "classify_input",
    decide_route,
    {
        "retry": "increment_retry",
        "end": END
    }
)
workflow.add_edge("increment_retry", "classify_input")

guardrail_app = workflow.compile()


class GuardrailResult:
    def __init__(self, is_allowed: bool, block_message: str, decision: str):
        self.is_allowed = is_allowed
        self.block_message = block_message
        self.decision = decision


async def run_guardrail(message: str, context: str = "") -> GuardrailResult:
    """사용자 메시지를 검사하여 GuardrailResult를 반환합니다."""
    
    # 1단계: 하드 차단 키워드 필터 (MALICIOUS)
    lower_msg = message.lower()
    for kw in MALICIOUS_KEYWORDS:
        if kw in lower_msg:
            return GuardrailResult(False, "부적절하거나 안전하지 않은 요청이 감지되었습니다. 건전한 전 투자를 위한 질문을 부탁드립니다.", "MALICIOUS")
            
    initial_state = GuardrailState(
        message=message,
        context=context,
        decision="",
        reasoning="",
        is_allowed=False,
        retries=0
    )
    
    final_state = await guardrail_app.ainvoke(initial_state)
    decision = final_state.get("decision", "OFF_TOPIC")
    
    # 2단계 정책 설정
    policy = os.getenv("TUTOR_GUARDRAIL_POLICY", "soft")
    
    is_allowed = (decision == "SAFE")
    block_message = ""
    
    if policy == "soft" and decision == "ADVICE":
        # 유연화 정책: ADVICE 판정시 대화 흐름을 끊지 않고 챗봇이 우회 교육답변을 하도록 통과
        is_allowed = True
        block_message = ""
    elif decision == "ADVICE":
        block_message = "죄송합니다만, 특정 종목에 대한 투자 자문(매수/매도 추천 등)은 자본시장법상 제공해 드릴 수 없습니다. 기업의 객관적인 재무 지표나 시장 동향에 대해서라면 답변해 드릴 수 있어요!"
    elif decision == "OFF_TOPIC":
        block_message = "저는 주식 및 금융/투자 학습을 돕기 위해 만들어진 튜터입니다. 관련이 없는 일상 대화나 다른 주제에 대해서는 도움을 드리기 어려워요."
    elif decision == "MALICIOUS":
        block_message = "부적절하거나 안전하지 않은 요청이 감지되었습니다. 건전한 투자 학습을 위한 질문을 부탁드립니다."
    elif decision == "PARSE_ERROR":
        block_message = PARSE_ERROR_MESSAGE
    elif not is_allowed:
        block_message = "서비스 범위 밖의 질문입니다."
            
    return GuardrailResult(
        is_allowed=is_allowed,
        block_message=block_message,
        decision=decision
    )
