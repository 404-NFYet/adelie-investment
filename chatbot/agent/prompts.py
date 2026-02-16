"""AI 튜터 에이전트용 시스템 프롬프트.

마크다운 기반 프롬프트 템플릿(chatbot/prompts/templates/)을 우선 로드하고,
템플릿을 찾을 수 없을 때만 내장 폴백 프롬프트를 사용한다.
"""

import logging

logger = logging.getLogger(__name__)

# --- 폴백 프롬프트 (마크다운 템플릿 로드 실패 시 사용) ---

_FALLBACK_SYSTEM_PROMPT = (
    "당신은 아델리에의 AI 학습 가이드입니다. "
    "한국 금융시장 초보자들에게 역사적 사례와 현재 상황을 비교하며 금융 지식을 전달합니다."
)

_FALLBACK_DIFFICULTY = {
    "beginner": "주식 초보자에게 일상적인 비유를 사용해서 아주 쉽게 설명해주세요.",
    "elementary": "기본 투자 용어를 아는 초급자에게 설명하세요. 간단한 수식이나 계산 예시 포함 가능합니다.",
    "intermediate": "투자 경험이 있는 중급자에게 설명하세요. 심화 재무 분석과 정량적 데이터를 포함해도 됩니다.",
}


def get_system_prompt(difficulty: str = "beginner", context: str = None) -> str:
    """난이도별 시스템 프롬프트를 반환한다.

    1순위: chatbot/prompts/templates/ 의 마크다운 템플릿
    2순위: 내장 폴백 문자열
    """
    # 마크다운 기반 프롬프트 시도
    try:
        from chatbot.prompts import load_prompt

        spec = load_prompt("tutor_system", difficulty=difficulty)
        prompt = spec.body

        # 난이도별 프롬프트 추가
        try:
            diff_spec = load_prompt(f"tutor_{difficulty}")
            prompt += "\n\n" + diff_spec.body
        except FileNotFoundError:
            pass

        if context:
            prompt += f"\n\n## 현재 컨텍스트\n{context}"

        return prompt
    except (ImportError, FileNotFoundError) as e:
        logger.debug("마크다운 프롬프트 로드 실패, 폴백 사용: %s", e)

    # 폴백: 내장 프롬프트
    prompt = _FALLBACK_SYSTEM_PROMPT
    prompt += "\n\n" + _FALLBACK_DIFFICULTY.get(difficulty, _FALLBACK_DIFFICULTY["beginner"])

    if context:
        prompt += f"\n\n## 현재 컨텍스트\n{context}"

    return prompt
