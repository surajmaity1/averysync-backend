from pydantic import BaseModel
from typing import Optional, Dict, Any


class LinksData(BaseModel):
    prev: str | None = None
    next: str | None = None


class PaginatedResponse(BaseModel):
    links: LinksData | None = None
    errors: Optional[Dict[str, Any]] = None
