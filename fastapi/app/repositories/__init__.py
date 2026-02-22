"""Repository 계층 - DB 쿼리 로직을 라우터에서 분리."""
from .base import GenericRepository
from .portfolio import PortfolioRepository
from .narrative import NarrativeRepository
from .briefing import BriefingRepository
from .glossary import GlossaryRepository

__all__ = [
    "GenericRepository",
    "PortfolioRepository",
    "NarrativeRepository",
    "BriefingRepository",
    "GlossaryRepository",
]
