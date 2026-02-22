"""Pytest configuration."""
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "fastapi"))
sys.path.insert(0, str(PROJECT_ROOT / "datapipeline"))
sys.path.insert(0, str(PROJECT_ROOT / "chatbot"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


def pytest_configure(config):
    """pytest-asyncio 자동 모드 설정."""
    config.addinivalue_line("markers", "asyncio: mark test as async")


@pytest.fixture(scope="session")
def project_root():
    return PROJECT_ROOT


# ── 테스트 DB 픽스처 (SQLite in-memory, 실제 DB 불필요) ──

@pytest.fixture(scope="session")
async def test_engine():
    """세션 범위 SQLite in-memory 엔진. 실제 PostgreSQL 연결 없이 테스트."""
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.core.database import Base

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield engine
        await engine.dispose()
    except Exception:
        yield None


@pytest.fixture
async def db_session(test_engine):
    """개별 테스트용 DB 세션. 각 테스트 후 롤백."""
    if test_engine is None:
        pytest.skip("DB 엔진 초기화 실패")

    from sqlalchemy.ext.asyncio import AsyncSession
    async with AsyncSession(test_engine) as session:
        yield session
        await session.rollback()


# ── LLM 모킹 픽스처 (OpenAI, Anthropic 실제 호출 차단) ──

def _make_openai_mock_response(content: str = "mock response") -> MagicMock:
    """OpenAI chat completions 응답 Mock 객체 생성."""
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    response.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    return response


@pytest.fixture
def mock_openai():
    """OpenAI AsyncClient 모킹. 실제 API 키 없이 LLM 응답 테스트."""
    with patch("openai.AsyncOpenAI") as mock_cls:
        instance = MagicMock()
        instance.chat.completions.create = AsyncMock(
            return_value=_make_openai_mock_response()
        )
        mock_cls.return_value = instance
        yield mock_cls


@pytest.fixture
def mock_openai_json():
    """OpenAI JSON 응답 모킹 (response_format=json_object 사용 라우터용)."""
    with patch("openai.AsyncOpenAI") as mock_cls:
        instance = MagicMock()
        instance.chat.completions.create = AsyncMock(
            return_value=_make_openai_mock_response(
                '{"term": "테스트", "definition_short": "테스트 정의", '
                '"definition_full": "테스트 상세 정의", "example": "테스트 예시"}'
            )
        )
        mock_cls.return_value = instance
        yield mock_cls


@pytest.fixture
def mock_anthropic():
    """Anthropic AsyncAnthropic 모킹."""
    with patch("anthropic.AsyncAnthropic") as mock_cls:
        instance = MagicMock()
        content_block = MagicMock()
        content_block.text = "mock anthropic response"
        response = MagicMock()
        response.content = [content_block]
        response.usage = MagicMock(input_tokens=10, output_tokens=20)
        instance.messages.create = AsyncMock(return_value=response)
        mock_cls.return_value = instance
        yield mock_cls


@pytest.fixture
def mock_all_llm(mock_openai, mock_anthropic):
    """OpenAI + Anthropic 동시 모킹 (파이프라인 통합 테스트용)."""
    yield {"openai": mock_openai, "anthropic": mock_anthropic}


# ── Redis 모킹 픽스처 ──

@pytest.fixture
def mock_redis():
    """Redis 클라이언트 모킹. 실제 Redis 없이 캐시 로직 테스트."""
    with patch("app.services.redis_cache.get_redis_cache") as mock_fn:
        cache_mock = MagicMock()
        cache_mock.client = None  # Redis 미연결 상태 시뮬레이션 (캐시 skip)
        mock_fn.return_value = cache_mock
        yield cache_mock
