"""피드백 관련 Pydantic 스키마."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    """인앱 피드백 생성 요청."""

    page: str = Field(..., max_length=50, description="현재 페이지 (home, narrative, portfolio, tutor, trading)")
    rating: Optional[int] = Field(None, ge=1, le=5, description="별점 (1~5)")
    category: Optional[str] = Field(None, max_length=20, description="카테고리 (design, feature, content, speed, other)")
    comment: Optional[str] = Field(None, max_length=1000, description="텍스트 의견")
    device_info: Optional[dict] = Field(None, description="디바이스 정보 (userAgent, screen, pwa여부)")


class BriefingFeedbackCreate(BaseModel):
    """브리핑 완독 피드백."""

    briefing_id: Optional[int] = None
    scenario_keyword: Optional[str] = None
    overall_rating: Literal["good", "neutral", "bad"] = Field(..., description="전체 평가")
    favorite_section: Optional[Literal["mirroring", "devils_advocate", "simulation", "action"]] = Field(
        None, description="좋았던 섹션"
    )


class ContentReactionCreate(BaseModel):
    """콘텐츠별 반응 (좋아요/싫어요)."""

    content_type: Literal["keyword_card", "narrative_step", "tutor_message"] = Field(
        ..., description="콘텐츠 유형"
    )
    content_id: str = Field(..., max_length=100, description="콘텐츠 식별자")
    reaction: Literal["like", "dislike"] = Field(..., description="반응 유형")


class AnalyticsEventBatch(BaseModel):
    """사용 행동 이벤트 배치."""

    events: list[dict] = Field(..., description="이벤트 목록")


class FeedbackSurveyCreate(BaseModel):
    """피드백 설문 제출."""

    ui_rating: int = Field(..., ge=1, le=5, description="UI/디자인 만족도")
    feature_rating: int = Field(..., ge=1, le=5, description="기능 편의성 만족도")
    content_rating: int = Field(..., ge=1, le=5, description="학습 콘텐츠 만족도")
    speed_rating: int = Field(..., ge=1, le=5, description="속도/안정성 만족도")
    overall_rating: int = Field(..., ge=1, le=5, description="전체 만족도")
    comment: Optional[str] = Field(None, max_length=2000, description="자유 의견")
    screenshot_url: Optional[str] = Field(None, max_length=500, description="에러 스크린샷 URL")


class FeedbackStats(BaseModel):
    """피드백 통계 응답."""

    total_count: int
    avg_rating: float
    category_distribution: dict
    page_distribution: dict
