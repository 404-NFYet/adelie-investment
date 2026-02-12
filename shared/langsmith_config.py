"""
LangSmith Tracing Configuration (shared)

LangSmith 트레이싱 설정 및 커스텀 메타데이터 관리.
chatbot/datapipeline 공통 사용. module_name 파라미터로 모듈 구분.
"""

import os
from typing import Any, Optional
from contextlib import contextmanager
from functools import wraps

from langsmith import Client
from langsmith.run_helpers import traceable

from .ai_config import get_settings


def setup_langsmith() -> bool:
    """
    LangSmith 환경 변수 설정.

    Returns:
        bool: 설정 성공 여부
    """
    settings = get_settings()

    if not settings.langsmith.tracing_enabled:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        return False

    if not settings.langsmith.api_key:
        return False

    # 환경에 따른 프로젝트명 설정
    project_name = f"{settings.langsmith.project_name}-{settings.environment}"

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith.api_key
    os.environ["LANGCHAIN_PROJECT"] = project_name
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith.endpoint

    return True


def get_langsmith_client() -> Optional[Client]:
    """
    LangSmith 클라이언트 반환.

    Returns:
        Optional[Client]: LangSmith 클라이언트 또는 None
    """
    settings = get_settings()

    if not settings.langsmith.api_key:
        return None

    return Client(
        api_key=settings.langsmith.api_key,
        api_url=settings.langsmith.endpoint,
    )


def with_metadata(
    run_name: Optional[str] = None,
    tags: Optional[list[str]] = None,
    metadata: Optional[dict[str, Any]] = None,
    module_name: str = "shared",
):
    """
    커스텀 메타데이터를 추가하는 데코레이터.

    Args:
        run_name: 실행 이름
        tags: 태그 목록
        metadata: 추가 메타데이터
        module_name: 모듈 식별자 ("chatbot" 또는 "datapipeline")
    """
    def decorator(func):
        settings = get_settings()

        if not settings.langsmith.tracing_enabled:
            return func

        # 기본 메타데이터
        default_metadata = {
            "environment": settings.environment,
            "module": module_name,
        }

        # 메타데이터 병합
        final_metadata = {**default_metadata, **(metadata or {})}

        return traceable(
            name=run_name,
            tags=tags,
            metadata=final_metadata,
        )(func)

    return decorator


@contextmanager
def trace_context(
    name: str,
    tags: Optional[list[str]] = None,
    metadata: Optional[dict[str, Any]] = None,
):
    """
    트레이싱 컨텍스트 매니저.

    Args:
        name: 트레이스 이름
        tags: 태그 목록
        metadata: 추가 메타데이터
    """
    settings = get_settings()

    if not settings.langsmith.tracing_enabled:
        yield
        return

    from langsmith.run_helpers import trace

    with trace(
        name=name,
        tags=tags or [],
        metadata=metadata or {},
    ):
        yield


def create_run_metadata(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    company_code: Optional[str] = None,
    module_name: str = "shared",
    **kwargs,
) -> dict[str, Any]:
    """
    표준화된 런 메타데이터 생성.

    Args:
        user_id: 사용자 ID
        session_id: 세션 ID
        company_code: 종목 코드
        module_name: 모듈 식별자 ("chatbot" 또는 "datapipeline")
        **kwargs: 추가 메타데이터

    Returns:
        dict: 메타데이터 딕셔너리
    """
    settings = get_settings()

    metadata = {
        "environment": settings.environment,
        "module": module_name,
        "version": "0.1.0",
    }

    if user_id:
        metadata["user_id"] = user_id
    if session_id:
        metadata["session_id"] = session_id
    if company_code:
        metadata["company_code"] = company_code

    metadata.update(kwargs)

    return metadata
