"""구조화된 로깅 설정."""

import logging
import sys
from typing import Optional


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
) -> logging.Logger:
    """
    애플리케이션 로깅 설정.

    Args:
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR)
        json_format: JSON 포맷 사용 여부 (프로덕션 권장)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    if json_format:
        import json

        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    "timestamp": self.formatTime(record),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
                if record.exc_info and record.exc_info[0]:
                    log_data["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_data, ensure_ascii=False)

        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "[%(asctime)s] %(name)s.%(funcName)s:%(lineno)d %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # narrative 네임스페이스 (레거시 호환)
    logger = logging.getLogger("narrative")
    logger.setLevel(log_level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # narrative_api 네임스페이스 (FastAPI 라우트용)
    api_logger = logging.getLogger("narrative_api")
    api_logger.setLevel(log_level)
    if not api_logger.handlers:
        api_handler = logging.StreamHandler(sys.stdout)
        api_handler.setLevel(log_level)
        api_handler.setFormatter(formatter)
        api_logger.addHandler(api_handler)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """모듈별 로거 반환."""
    base = "narrative"
    if name:
        return logging.getLogger(f"{base}.{name}")
    return logging.getLogger(base)
