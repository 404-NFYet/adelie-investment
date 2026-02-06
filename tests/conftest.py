"""Pytest configuration."""
import os, sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend-api"))
sys.path.insert(0, str(PROJECT_ROOT / "data-pipeline"))
sys.path.insert(0, str(PROJECT_ROOT / "ai-module"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


def pytest_configure(config):
    """pytest-asyncio 자동 모드 설정."""
    config.addinivalue_line("markers", "asyncio: mark test as async")


@pytest.fixture(scope="session")
def project_root():
    return PROJECT_ROOT

