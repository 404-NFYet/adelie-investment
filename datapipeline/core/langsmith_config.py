"""LangSmith Tracing Configuration — datapipeline 모듈 바인딩."""

from functools import partial
from typing import Any, Optional

from shared.langsmith_config import (
    setup_langsmith,
    get_langsmith_client,
    with_metadata as _with_metadata,
    trace_context,
    create_run_metadata as _create_run_metadata,
)

# module_name="datapipeline" 바인딩
with_metadata = partial(_with_metadata, module_name="datapipeline")
create_run_metadata = partial(_create_run_metadata, module_name="datapipeline")

# 모듈 로드 시 LangSmith 설정
_langsmith_enabled = setup_langsmith()

__all__ = [
    "setup_langsmith",
    "get_langsmith_client",
    "with_metadata",
    "trace_context",
    "create_run_metadata",
]
