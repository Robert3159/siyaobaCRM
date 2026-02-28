"""与前端约定的统一成功响应格式：{ code: '0000', data }"""

from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_json(data: Any, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": "0000", "data": jsonable_encoder(data)},
    )
