"""
Perplexity Service

Perplexity API를 통한 웹 검색 기능 제공.
검색 결과 생성은 OpenAI를 사용하고, 실시간 검색만 Perplexity 사용.
"""

from typing import Any, Optional

from openai import OpenAI, AsyncOpenAI

from ..core.config import get_settings
from ..core.langsmith_config import with_metadata


class PerplexityService:
    """Perplexity API 서비스 싱글톤."""
    
    _instance: Optional["PerplexityService"] = None
    _client: Optional[OpenAI] = None
    _async_client: Optional[AsyncOpenAI] = None
    
    def __new__(cls) -> "PerplexityService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            settings = get_settings()
            # Perplexity는 OpenAI 호환 API 사용
            self._client = OpenAI(
                api_key=settings.perplexity.api_key,
                base_url=settings.perplexity.base_url,
            )
            self._async_client = AsyncOpenAI(
                api_key=settings.perplexity.api_key,
                base_url=settings.perplexity.base_url,
            )
    
    @property
    def client(self) -> OpenAI:
        """동기 클라이언트 반환."""
        return self._client
    
    @property
    def async_client(self) -> AsyncOpenAI:
        """비동기 클라이언트 반환."""
        return self._async_client


def get_perplexity_service() -> PerplexityService:
    """Perplexity 서비스 인스턴스 반환."""
    return PerplexityService()


@with_metadata(run_name="perplexity_search", tags=["perplexity", "search"])
def search(
    query: str,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    return_citations: bool = True,
    return_images: bool = False,
    search_recency_filter: Optional[str] = None,
) -> dict[str, Any]:
    """
    Perplexity 웹 검색 수행 (동기).
    
    Args:
        query: 검색 쿼리
        model: 모델명 (기본: sonar-pro)
        max_tokens: 최대 토큰 수
        return_citations: 인용 출처 반환 여부
        return_images: 이미지 반환 여부
        search_recency_filter: 검색 기간 필터 (day, week, month, year)
    
    Returns:
        dict: 검색 결과
            - content: 검색 결과 텍스트
            - citations: 인용 출처 목록 (return_citations=True일 때)
    
    Example:
        result = search("삼성전자 최근 실적 발표")
        print(result["content"])
        print(result["citations"])
    """
    settings = get_settings()
    service = get_perplexity_service()
    
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful search assistant. "
                "Provide accurate, up-to-date information with citations. "
                "Answer in Korean when the query is in Korean."
            ),
        },
        {"role": "user", "content": query},
    ]
    
    # 추가 파라미터
    extra_params = {}
    if return_citations:
        extra_params["return_citations"] = True
    if return_images:
        extra_params["return_images"] = True
    if search_recency_filter:
        extra_params["search_recency_filter"] = search_recency_filter
    
    response = service.client.chat.completions.create(
        model=model or settings.perplexity.model,
        messages=messages,
        max_tokens=max_tokens or settings.perplexity.max_tokens,
        **extra_params,
    )
    
    result = {
        "content": response.choices[0].message.content,
        "model": response.model,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
        },
    }
    
    # 인용 정보 추가
    if hasattr(response, "citations") and response.citations:
        result["citations"] = response.citations
    
    return result


@with_metadata(run_name="perplexity_search_async", tags=["perplexity", "search", "async"])
async def search_async(
    query: str,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    return_citations: bool = True,
    return_images: bool = False,
    search_recency_filter: Optional[str] = None,
) -> dict[str, Any]:
    """
    Perplexity 웹 검색 수행 (비동기).
    
    Args:
        query: 검색 쿼리
        model: 모델명 (기본: sonar-pro)
        max_tokens: 최대 토큰 수
        return_citations: 인용 출처 반환 여부
        return_images: 이미지 반환 여부
        search_recency_filter: 검색 기간 필터 (day, week, month, year)
    
    Returns:
        dict: 검색 결과
    """
    settings = get_settings()
    service = get_perplexity_service()
    
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful search assistant. "
                "Provide accurate, up-to-date information with citations. "
                "Answer in Korean when the query is in Korean."
            ),
        },
        {"role": "user", "content": query},
    ]
    
    extra_params = {}
    if return_citations:
        extra_params["return_citations"] = True
    if return_images:
        extra_params["return_images"] = True
    if search_recency_filter:
        extra_params["search_recency_filter"] = search_recency_filter
    
    response = await service.async_client.chat.completions.create(
        model=model or settings.perplexity.model,
        messages=messages,
        max_tokens=max_tokens or settings.perplexity.max_tokens,
        **extra_params,
    )
    
    result = {
        "content": response.choices[0].message.content,
        "model": response.model,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
        },
    }
    
    if hasattr(response, "citations") and response.citations:
        result["citations"] = response.citations
    
    return result


@with_metadata(run_name="perplexity_news_search", tags=["perplexity", "news"])
def search_news(
    query: str,
    recency: str = "week",
    max_tokens: Optional[int] = None,
) -> dict[str, Any]:
    """
    최신 뉴스 검색.
    
    Args:
        query: 검색 쿼리
        recency: 검색 기간 (day, week, month)
        max_tokens: 최대 토큰 수
    
    Returns:
        dict: 뉴스 검색 결과
    
    Example:
        news = search_news("반도체 산업 동향", recency="week")
    """
    return search(
        query=query,
        max_tokens=max_tokens,
        return_citations=True,
        search_recency_filter=recency,
    )


@with_metadata(run_name="perplexity_news_search_async", tags=["perplexity", "news", "async"])
async def search_news_async(
    query: str,
    recency: str = "week",
    max_tokens: Optional[int] = None,
) -> dict[str, Any]:
    """
    최신 뉴스 검색 (비동기).
    
    Args:
        query: 검색 쿼리
        recency: 검색 기간 (day, week, month)
        max_tokens: 최대 토큰 수
    
    Returns:
        dict: 뉴스 검색 결과
    """
    return await search_async(
        query=query,
        max_tokens=max_tokens,
        return_citations=True,
        search_recency_filter=recency,
    )
