"""Rate limiter 설정 모듈 (순환 참조 방지용 별도 모듈)."""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
