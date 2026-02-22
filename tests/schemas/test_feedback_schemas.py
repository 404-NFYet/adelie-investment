"""피드백 관련 스키마 유닛 테스트."""

import pytest
from pydantic import ValidationError

from app.schemas.feedback import (
    BriefingFeedbackCreate,
    ContentReactionCreate,
    FeedbackCreate,
    FeedbackSurveyCreate,
)


class TestFeedbackCreate:
    """인앱 피드백 스키마 테스트."""

    def test_valid_feedback(self):
        fb = FeedbackCreate(page="home", rating=4, category="design", comment="좋아요")
        assert fb.page == "home"
        assert fb.rating == 4

    def test_page_required(self):
        with pytest.raises(ValidationError):
            FeedbackCreate(rating=3)

    def test_rating_range_valid(self):
        for r in range(1, 6):
            fb = FeedbackCreate(page="home", rating=r)
            assert fb.rating == r

    def test_rating_out_of_range(self):
        with pytest.raises(ValidationError):
            FeedbackCreate(page="home", rating=0)
        with pytest.raises(ValidationError):
            FeedbackCreate(page="home", rating=6)

    def test_rating_optional(self):
        fb = FeedbackCreate(page="home")
        assert fb.rating is None

    def test_comment_max_length(self):
        fb = FeedbackCreate(page="home", comment="a" * 1000)
        assert len(fb.comment) == 1000
        with pytest.raises(ValidationError):
            FeedbackCreate(page="home", comment="a" * 1001)


class TestBriefingFeedbackCreate:
    """브리핑 피드백 스키마 테스트."""

    def test_valid_ratings(self):
        for rating in ("good", "neutral", "bad"):
            fb = BriefingFeedbackCreate(overall_rating=rating)
            assert fb.overall_rating == rating

    def test_invalid_rating_rejected(self):
        with pytest.raises(ValidationError):
            BriefingFeedbackCreate(overall_rating="excellent")

    def test_favorite_section_valid(self):
        for section in ("mirroring", "devils_advocate", "simulation", "action"):
            fb = BriefingFeedbackCreate(overall_rating="good", favorite_section=section)
            assert fb.favorite_section == section

    def test_favorite_section_invalid(self):
        with pytest.raises(ValidationError):
            BriefingFeedbackCreate(overall_rating="good", favorite_section="unknown")


class TestContentReactionCreate:
    """콘텐츠 반응 스키마 테스트."""

    def test_valid_combinations(self):
        for ct in ("keyword_card", "narrative_step", "tutor_message"):
            for reaction in ("like", "dislike"):
                r = ContentReactionCreate(content_type=ct, content_id="test-1", reaction=reaction)
                assert r.content_type == ct
                assert r.reaction == reaction

    def test_invalid_type_rejected(self):
        with pytest.raises(ValidationError):
            ContentReactionCreate(content_type="invalid", content_id="test", reaction="like")

    def test_invalid_reaction_rejected(self):
        with pytest.raises(ValidationError):
            ContentReactionCreate(content_type="keyword_card", content_id="test", reaction="love")


class TestFeedbackSurveyCreate:
    """피드백 설문 스키마 테스트."""

    def test_valid_survey(self):
        s = FeedbackSurveyCreate(
            ui_rating=4, feature_rating=3, content_rating=5,
            speed_rating=2, overall_rating=4
        )
        assert s.overall_rating == 4

    def test_rating_range_1_to_5(self):
        # 유효 범위
        for r in range(1, 6):
            s = FeedbackSurveyCreate(
                ui_rating=r, feature_rating=r, content_rating=r,
                speed_rating=r, overall_rating=r
            )
            assert s.ui_rating == r

    def test_rating_below_range(self):
        with pytest.raises(ValidationError):
            FeedbackSurveyCreate(
                ui_rating=0, feature_rating=3, content_rating=3,
                speed_rating=3, overall_rating=3
            )

    def test_rating_above_range(self):
        with pytest.raises(ValidationError):
            FeedbackSurveyCreate(
                ui_rating=6, feature_rating=3, content_rating=3,
                speed_rating=3, overall_rating=3
            )

    def test_comment_optional(self):
        s = FeedbackSurveyCreate(
            ui_rating=3, feature_rating=3, content_rating=3,
            speed_rating=3, overall_rating=3
        )
        assert s.comment is None

    def test_screenshot_url_optional(self):
        s = FeedbackSurveyCreate(
            ui_rating=3, feature_rating=3, content_rating=3,
            speed_rating=3, overall_rating=3,
            screenshot_url="/minio/feedback-screenshots/test.png"
        )
        assert s.screenshot_url is not None
