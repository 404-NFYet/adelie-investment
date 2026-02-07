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
    logger = logging.getLogger("narrative")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 핸들러 중복 방지
    if logger.handlers:
        return logger
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    
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
        
        handler.setFormatter(JsonFormatter())
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """모듈별 로거 반환."""
    base = "narrative"
    if name:
        return logging.getLogger(f"{base}.{name}")
    return logging.getLogger(base)
