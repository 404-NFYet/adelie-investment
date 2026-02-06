"""Config package - re-exports from core to avoid duplication.

config/langsmith.py는 core/langsmith_config.py와 중복되므로,
이 패키지에서는 core 모듈을 재수출합니다.
"""

from ai_module.core.langsmith_config import (  # noqa: F401
    setup_langsmith,
    get_langsmith_client,
    with_metadata,
    trace_context,
    create_run_metadata,
)
