"""
LangSmith Tracing Configuration

LangSmith 트레이싱 설정 및 커스텀 메타데이터 관리.
"""

import os
from typing import Any, Optional
from contextlib import contextmanager
from functools import wraps

from langsmith import Client
from langsmith.run_helpers import traceable

from .config import get_settings


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
):
    """
    커스텀 메타데이터를 추가하는 데코레이터.
    
    Args:
        run_name: 실행 이름
        tags: 태그 목록
        metadata: 추가 메타데이터
    
    Example:
        @with_metadata(
            run_name="supply_chain_query",
            tags=["neo4j", "supply-chain"],
            metadata={"company": "삼성전자"}
        )
        async def query_supply_chain(company_name: str):
            ...
    """
    def decorator(func):
        settings = get_settings()
        
        if not settings.langsmith.tracing_enabled:
            return func
        
        # 기본 메타데이터
        default_metadata = {
            "environment": settings.environment,
            "module": "chatbot",
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
    
    Example:
        with trace_context("document_processing", tags=["pdf"]):
            result = process_document(doc)
    """
    settings = get_settings()
    
    if not settings.langsmith.tracing_enabled:
        yield
        return
    
    # langsmith의 trace context 사용
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
    **kwargs,
) -> dict[str, Any]:
    """
    표준화된 런 메타데이터 생성.
    
    Args:
        user_id: 사용자 ID
        session_id: 세션 ID
        company_code: 종목 코드
        **kwargs: 추가 메타데이터
    
    Returns:
        dict: 메타데이터 딕셔너리
    """
    settings = get_settings()
    
    metadata = {
        "environment": settings.environment,
        "module": "chatbot",
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


# 모듈 로드 시 LangSmith 설정
_langsmith_enabled = setup_langsmith()
