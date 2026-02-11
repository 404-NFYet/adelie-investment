"""
OpenAI Service

OpenAI API 클라이언트 및 completion 함수 제공.
"""

import base64
from pathlib import Path
from typing import Any, Optional, Union

from openai import OpenAI, AsyncOpenAI

from ..core.config import get_settings
from ..core.langsmith_config import with_metadata


class OpenAIService:
    """OpenAI API 서비스 싱글톤."""
    
    _instance: Optional["OpenAIService"] = None
    _client: Optional[OpenAI] = None
    _async_client: Optional[AsyncOpenAI] = None
    
    def __new__(cls) -> "OpenAIService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            settings = get_settings()
            self._client = OpenAI(api_key=settings.openai.api_key)
            self._async_client = AsyncOpenAI(api_key=settings.openai.api_key)
    
    @property
    def client(self) -> OpenAI:
        """동기 클라이언트 반환."""
        return self._client
    
    @property
    def async_client(self) -> AsyncOpenAI:
        """비동기 클라이언트 반환."""
        return self._async_client


def get_openai_service() -> OpenAIService:
    """OpenAI 서비스 인스턴스 반환."""
    return OpenAIService()


@with_metadata(run_name="chat_completion", tags=["openai", "chat"])
def chat_completion(
    messages: list[dict[str, str]],
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    **kwargs,
) -> str:
    """
    OpenAI Chat Completion 호출 (동기).
    
    Args:
        messages: 대화 메시지 목록
        model: 모델명 (기본: gpt-4o-mini)
        temperature: 온도 파라미터
        max_tokens: 최대 토큰 수
        **kwargs: 추가 파라미터
    
    Returns:
        str: 생성된 응답 텍스트
    
    Example:
        response = chat_completion([
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ])
    """
    settings = get_settings()
    service = get_openai_service()
    
    response = service.client.chat.completions.create(
        model=model or settings.openai.default_model,
        messages=messages,
        temperature=temperature if temperature is not None else settings.openai.temperature,
        max_tokens=max_tokens or settings.openai.max_tokens,
        **kwargs,
    )
    
    return response.choices[0].message.content


@with_metadata(run_name="chat_completion_async", tags=["openai", "chat", "async"])
async def chat_completion_async(
    messages: list[dict[str, str]],
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    **kwargs,
) -> str:
    """
    OpenAI Chat Completion 호출 (비동기).
    
    Args:
        messages: 대화 메시지 목록
        model: 모델명 (기본: gpt-4o-mini)
        temperature: 온도 파라미터
        max_tokens: 최대 토큰 수
        **kwargs: 추가 파라미터
    
    Returns:
        str: 생성된 응답 텍스트
    """
    settings = get_settings()
    service = get_openai_service()
    
    response = await service.async_client.chat.completions.create(
        model=model or settings.openai.default_model,
        messages=messages,
        temperature=temperature if temperature is not None else settings.openai.temperature,
        max_tokens=max_tokens or settings.openai.max_tokens,
        **kwargs,
    )
    
    return response.choices[0].message.content


def _encode_image(image_path: Union[str, Path]) -> str:
    """이미지를 base64로 인코딩."""
    path = Path(image_path)
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _get_image_media_type(image_path: Union[str, Path]) -> str:
    """이미지 파일의 media type 반환."""
    suffix = Path(image_path).suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return media_types.get(suffix, "image/jpeg")


@with_metadata(run_name="vision_completion", tags=["openai", "vision"])
def vision_completion(
    prompt: str,
    image_paths: list[Union[str, Path]],
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    **kwargs,
) -> str:
    """
    OpenAI Vision Completion 호출 (이미지 분석).
    
    Args:
        prompt: 분석 요청 텍스트
        image_paths: 이미지 파일 경로 목록
        model: 모델명 (기본: gpt-4o)
        max_tokens: 최대 토큰 수
        **kwargs: 추가 파라미터
    
    Returns:
        str: 이미지 분석 결과 텍스트
    
    Example:
        result = vision_completion(
            prompt="이 차트를 분석해주세요.",
            image_paths=["chart.png"]
        )
    """
    settings = get_settings()
    service = get_openai_service()
    
    # 이미지 컨텐츠 구성
    content = [{"type": "text", "text": prompt}]
    
    for image_path in image_paths:
        base64_image = _encode_image(image_path)
        media_type = _get_image_media_type(image_path)
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{media_type};base64,{base64_image}",
            },
        })
    
    response = service.client.chat.completions.create(
        model=model or settings.openai.vision_model,
        messages=[{"role": "user", "content": content}],
        max_tokens=max_tokens or settings.openai.max_tokens,
        **kwargs,
    )
    
    return response.choices[0].message.content


@with_metadata(run_name="vision_completion_async", tags=["openai", "vision", "async"])
async def vision_completion_async(
    prompt: str,
    image_paths: list[Union[str, Path]],
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    **kwargs,
) -> str:
    """
    OpenAI Vision Completion 호출 (비동기).
    
    Args:
        prompt: 분석 요청 텍스트
        image_paths: 이미지 파일 경로 목록
        model: 모델명 (기본: gpt-4o)
        max_tokens: 최대 토큰 수
        **kwargs: 추가 파라미터
    
    Returns:
        str: 이미지 분석 결과 텍스트
    """
    settings = get_settings()
    service = get_openai_service()
    
    content = [{"type": "text", "text": prompt}]
    
    for image_path in image_paths:
        base64_image = _encode_image(image_path)
        media_type = _get_image_media_type(image_path)
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{media_type};base64,{base64_image}",
            },
        })
    
    response = await service.async_client.chat.completions.create(
        model=model or settings.openai.vision_model,
        messages=[{"role": "user", "content": content}],
        max_tokens=max_tokens or settings.openai.max_tokens,
        **kwargs,
    )
    
    return response.choices[0].message.content
