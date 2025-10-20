from pydantic import BaseModel


class ApiErrorDetail(BaseModel):
    source: str | None = None
    title: str | None = None
    description: str | None = None


class ApiErrorResponse(BaseModel):
    statusCode: int
    message: str
    errors: list[ApiErrorDetail]
    authenticated: bool | None = None