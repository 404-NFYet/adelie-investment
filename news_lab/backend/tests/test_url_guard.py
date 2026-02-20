from app.services.url_guard import UrlValidationError, validate_public_article_url


def test_validate_public_url_ok():
    url = validate_public_article_url("https://www.marketwatch.com/story/test")
    assert url.startswith("https://")


def test_validate_localhost_blocked():
    try:
        validate_public_article_url("http://localhost:8080/test")
        assert False, "expected UrlValidationError"
    except UrlValidationError:
        assert True


def test_validate_private_ip_blocked():
    try:
        validate_public_article_url("http://127.0.0.1/test")
        assert False, "expected UrlValidationError"
    except UrlValidationError:
        assert True


def test_validate_scheme_blocked():
    try:
        validate_public_article_url("file:///etc/passwd")
        assert False, "expected UrlValidationError"
    except UrlValidationError:
        assert True
