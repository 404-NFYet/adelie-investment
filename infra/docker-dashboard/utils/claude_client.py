"""Claude API 스트리밍 wrapper — 팀원 챗봇용"""

import anthropic

from config import CLAUDE_API_KEY, CLAUDE_MODEL


def stream_response(messages: list[dict], system: str):
    """Claude API 스트리밍 — 텍스트 청크를 generator로 yield"""
    if not CLAUDE_API_KEY:
        yield "⚠️ CLAUDE_API_KEY가 설정되지 않았습니다. 환경변수를 확인하세요."
        return

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        system=system,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text
