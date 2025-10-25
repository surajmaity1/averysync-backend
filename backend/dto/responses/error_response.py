from pydantic import BaseModel
from enum import Enum
from typing import Dict


class ApiErrorSource(Enum):
    PARAMETER = 'parameter'


class ApiErrorDetail(BaseModel):
    source: Dict[ApiErrorSource, str] | None = None
    title: str | None = None
    description: str | None = None


class ApiErrorResponse(BaseModel):
    statusCode: int
    message: str
    errors: list[ApiErrorDetail]
    authenticated: bool | None = None
