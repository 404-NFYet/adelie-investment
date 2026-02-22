"""Adelie 커스텀 예외 계층.

사용법:
    from app.core.exceptions import NotFoundError, UnauthorizedError

    # 라우터에서
    raise NotFoundError("키워드")
    raise UnauthorizedError()
    raise ForbiddenError()
    raise BadRequestError("날짜 형식이 올바르지 않습니다")
    raise ServiceUnavailableError("OpenAI API")
"""


class AdelieException(Exception):
    """Adelie 플랫폼 기반 예외 클래스.

    main.py의 adelie_exception_handler에서 통일된 JSON 응답으로 변환된다.
    {
        "status": "error",
        "code": "<code>",
        "message": "<message>"
    }
    """

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class NotFoundError(AdelieException):
    """404 - 리소스 없음."""

    def __init__(self, resource: str = "리소스") -> None:
        super().__init__(404, "NOT_FOUND", f"{resource}을(를) 찾을 수 없습니다")


class UnauthorizedError(AdelieException):
    """401 - 인증 필요."""

    def __init__(self, message: str = "인증이 필요합니다") -> None:
        super().__init__(401, "UNAUTHORIZED", message)


class ForbiddenError(AdelieException):
    """403 - 권한 없음."""

    def __init__(self, message: str = "접근 권한이 없습니다") -> None:
        super().__init__(403, "FORBIDDEN", message)


class BadRequestError(AdelieException):
    """400 - 잘못된 요청."""

    def __init__(self, message: str = "잘못된 요청입니다") -> None:
        super().__init__(400, "BAD_REQUEST", message)


class ConflictError(AdelieException):
    """409 - 리소스 충돌."""

    def __init__(self, resource: str = "리소스") -> None:
        super().__init__(409, "CONFLICT", f"{resource}이(가) 이미 존재합니다")


class ServiceUnavailableError(AdelieException):
    """503 - 외부 서비스 사용 불가."""

    def __init__(self, service: str = "서비스") -> None:
        super().__init__(503, "SERVICE_UNAVAILABLE", f"{service}를 현재 사용할 수 없습니다")
