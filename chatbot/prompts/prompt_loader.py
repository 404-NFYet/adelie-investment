"""프롬프트 로더: datapipeline 공유 로더 기반, chatbot 전용 templates 디렉토리.

chatbot/prompts/templates/ 의 튜터 전용 프롬프트를 로드한다.
로더 구현은 datapipeline.prompts.prompt_loader에 위임.
"""

from pathlib import Path

from datapipeline.prompts.prompt_loader import load_prompt as _load_prompt, PromptSpec

_CHATBOT_TEMPLATES = Path(__file__).resolve().parent / "templates"

# 하위 호환: test_prompt_loader.py에서 _DEFAULT_DIR 참조
_DEFAULT_DIR = _CHATBOT_TEMPLATES


def load_prompt(name: str, prompts_dir=None, **kwargs):
    """chatbot 전용 프롬프트 로드 (기본 디렉토리: chatbot/prompts/templates/)."""
    return _load_prompt(name, prompts_dir=prompts_dir or _CHATBOT_TEMPLATES, **kwargs)


__all__ = ["load_prompt", "PromptSpec"]
