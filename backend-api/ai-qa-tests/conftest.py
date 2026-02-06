"""
AI QA 테스트 설정
"""
import pytest
import asyncio

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def api_base_url():
    """API base URL fixture"""
    return "http://localhost:8082/api/v1"
