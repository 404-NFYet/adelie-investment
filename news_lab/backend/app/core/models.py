from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


Market = Literal["KR", "US"]
Difficulty = Literal["beginner", "elementary", "intermediate"]


class SourceItem(BaseModel):
    id: str
    name: str
    homepage: HttpUrl
    feed_url: HttpUrl


class HeadlineItem(BaseModel):
    title: str
    url: HttpUrl
    source_id: str
    source: str
    published_at: datetime | None = None
    image_url: HttpUrl | None = None


class AnalyzeRequest(BaseModel):
    url: HttpUrl
    difficulty: Difficulty = "beginner"
    market: Market = "KR"


class ArticlePayload(BaseModel):
    title: str
    url: HttpUrl
    source: str
    published_at: str | None = None
    content: str
    image_url: HttpUrl | None = None
    content_type: Literal["article", "youtube"] | None = None


class GlossaryItem(BaseModel):
    term: str
    definition: str
    kind: Literal["word", "phrase"]
    importance: int = Field(default=1, ge=1, le=5)


class SixWPayload(BaseModel):
    who: str = ""
    what: str = ""
    when: str = ""
    where: str = ""
    why: str = ""
    how: str = ""


class ExplainModePayload(BaseModel):
    content_marked: str
    highlighted_terms: list[dict] = Field(default_factory=list)
    glossary: list[GlossaryItem] = Field(default_factory=list)
    adelie_title: str | None = None
    lede: str | None = None
    six_w: SixWPayload | None = None
    takeaways: list[str] = Field(default_factory=list)


class NewsletterModePayload(BaseModel):
    background: str
    importance: str
    concepts: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    takeaways: list[str] = Field(default_factory=list)
    content_marked: str
    highlighted_terms: list[dict] = Field(default_factory=list)
    glossary: list[GlossaryItem] = Field(default_factory=list)
    adelie_title: str | None = None
    lede: str | None = None
    six_w: SixWPayload | None = None


class AnalyzeResponse(BaseModel):
    article: ArticlePayload
    explain_mode: ExplainModePayload
    newsletter_mode: NewsletterModePayload
    highlighted_terms: list[dict] = Field(default_factory=list)
    glossary: list[GlossaryItem] = Field(default_factory=list)
    fetch_status: Literal["ok", "missing_url", "fetch_failed", "parse_failed"] = "ok"
    cached: bool = False

    content_quality_score: int = 0
    quality_flags: list[str] = Field(default_factory=list)
    article_domain: str = ""
    is_finance_article: bool = False
    chart_ready: bool = False
    chart_unavailable_reason: str | None = None


class VisualizeRequest(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    data_context: str = Field(default="", max_length=5000)


class TermExplainResponse(BaseModel):
    term: str
    difficulty: Difficulty
    explanation: str
    source: str | None = None
