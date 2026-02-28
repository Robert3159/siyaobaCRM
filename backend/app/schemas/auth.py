from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    user: str  # 用户名，登录用
    password: str
    turnstile_token: str = ""


class SendEmailCodeRequest(BaseModel):
    email: EmailStr


class RegisterRequest(BaseModel):
    user: str  # 用户名
    alias: str = ""  # 花名，可选
    email: EmailStr
    code: str
    password: str = Field(..., min_length=6, max_length=32)
    turnstile_token: str


class ResetPasswordByEmailRequest(BaseModel):
    email: EmailStr
    code: str
    password: str = Field(..., min_length=6, max_length=32)


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
