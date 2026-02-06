"""시각화 생성 도구 - claude-3-5-haiku 또는 gpt-4o로 Plotly 코드 생성"""
import os, json, logging, re
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

VISUALIZATION_SYSTEM_PROMPT = """Python Plotly를 사용하여 시각화 코드를 작성하세요.

## 디자인 규칙
- 주 색상: #FF6B00, 보조: #4A90D9
- 배경: paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
- 폰트: 'IBM Plex Sans KR', size=12, color='#4E5968'
- 그리드: color='#F2F4F6'
- 축: color='#8B95A1', size=11
- 마진: dict(t=50, b=60, l=60, r=30)

## Plotly API 주의사항
- go.Scatter의 textposition: 'top center', 'bottom center' 등만 유효 ('outside'는 Bar 전용!)
- titlefont는 deprecated, title_font 사용
- include_plotlyjs='cdn'으로 경량 HTML

## 규칙
- Y축에 단위 표기 (예: "PER (배)")
- 데이터에 값 표시
- fig.write_html('/output/chart.html', include_plotlyjs='cdn', full_html=True)
- 데이터가 제공되지 않은 경우, 요청 주제에 맞는 합리적인 예시 데이터를 직접 생성하여 차트를 만드세요.
- 반드시 Python 코드만 출력하세요. 설명, 사과, 안내 문구를 절대 포함하지 마세요.
- 코드 블록 없이 바로 import부터 시작하세요."""


def _extract_python_code(text: str) -> str | None:
    """LLM 응답에서 Python 코드를 추출한다. 코드가 아닌 텍스트면 None 반환."""
    if not text or not text.strip():
        return None

    # 마크다운 코드블록에서 추출
    if "```python" in text:
        code = text.split("```python")[1].split("```")[0].strip()
    elif "```" in text:
        code = text.split("```")[1].split("```")[0].strip()
    else:
        code = text.strip()

    # 추출된 결과가 실제 Python 코드인지 검증
    # import 또는 from으로 시작하지 않고, plotly/fig 키워드가 없으면 코드가 아님
    first_line = code.split("\n")[0].strip()
    has_import = first_line.startswith("import ") or first_line.startswith("from ")
    has_plotly_keyword = "plotly" in code or "fig" in code or "write_html" in code

    if not has_import and not has_plotly_keyword:
        logger.warning("LLM 응답이 코드가 아님 (첫 줄: %s)", first_line[:80])
        return None

    return code


@tool
def generate_visualization(description: str, data_context: str = "") -> dict:
    """사용자 요청에 맞는 Plotly 시각화 코드를 생성합니다.
    
    Args:
        description: 시각화 설명
        data_context: 데이터 (JSON 또는 텍스트)
    """
    # claude-3-5-haiku 우선, fallback gpt-4o
    code = _generate_with_claude(description, data_context)
    if code is None:
        code = _generate_with_openai(description, data_context)
    
    if code:
        return {"code": code, "type": "plotly_code"}
    return {"error": "코드 생성 실패"}


def _build_user_prompt(desc: str, data: str) -> str:
    """시각화 요청 프롬프트 구성."""
    prompt = f"시각화: {desc}"
    if data and data.strip():
        prompt += f"\n\n제공된 데이터:\n{data}"
    else:
        prompt += "\n\n데이터가 제공되지 않았습니다. 주제에 맞는 합리적인 예시 데이터를 생성하여 차트를 만드세요."
    return prompt


def _generate_with_claude(desc, data):
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=2000,
            system=VISUALIZATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(desc, data)}],
            temperature=0.2,
        )
        return _extract_python_code(response.content[0].text)
    except Exception as e:
        logger.warning("Claude 코드 생성 실패: %s", e)
        return None

def _generate_with_openai(desc, data):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": VISUALIZATION_SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(desc, data)},
            ],
            max_tokens=2000,
            temperature=0.2,
        )
        return _extract_python_code(response.choices[0].message.content)
    except Exception as e:
        logger.warning("OpenAI 코드 생성 실패: %s", e)
        return None
