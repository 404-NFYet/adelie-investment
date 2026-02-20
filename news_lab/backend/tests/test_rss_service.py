from app.services.rss_service import _is_title_quality_ok


def test_title_quality_rejects_mojibake():
    assert not _is_title_quality_ok("ì´ ëíµë ¹ R&D ìíê³")


def test_title_quality_rejects_too_short():
    assert not _is_title_quality_ok("속보")


def test_title_quality_accepts_normal_title():
    assert _is_title_quality_ok("코스피 장중 2,800선 회복... 외국인 순매수 확대")
