from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_422_UNPROCESSABLE_ENTITY


class BusinessError(Exception):
    """
    统一业务异常。

    符合规则书的要求：通过业务异常承载 code 与 message，而不是返回裸字符串。
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def business_error_handler(_: Request, exc: BusinessError) -> JSONResponse:
    # 认证相关错误返回 401
    if exc.code in ("UNAUTHENTICATED", "INVALID_TOKEN", "TOKEN_EXPIRED"):
        status_code = HTTP_401_UNAUTHORIZED
    else:
        status_code = HTTP_400_BAD_REQUEST
    
    return JSONResponse(
        status_code=status_code,
        content={"code": exc.code, "message": exc.message, "msg": exc.message},
    )


def validation_error_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": "VALIDATION_ERROR",
            "message": "请求参数校验失败",
            "msg": "请求参数校验失败",
            "details": exc.errors(),
        },
    )
