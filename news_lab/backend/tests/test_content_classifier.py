from app.services.content_classifier import classify_finance_article


def test_classify_finance_article_true():
    result = classify_finance_article(
        title="코스피 2% 상승, 반도체 실적 개선 기대",
        content="환율은 1,360원대로 하락했고 금리 인하 기대가 커지며 외국인 순매수가 확대됐다.",
        source="hankyung.com",
    )
    assert result.is_finance_article is True
    assert result.score >= 3


def test_classify_finance_article_false_for_politics():
    result = classify_finance_article(
        title="민주당 복당 신청 관련 정치권 공방",
        content="국회와 여야가 재판 일정과 법안 처리 방향을 두고 충돌했다.",
        source="example.com",
    )
    assert result.is_finance_article is False
