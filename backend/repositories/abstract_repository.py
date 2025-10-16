from abc import ABC
from typing import Generic, TypeVar
from pydantic import BaseModel


T = TypeVar('T', bound = BaseModel)


class AbstractRepository(ABC, Generic[T]):
    pass


class AbstractUserRepository(AbstractRepository[T]):
    pass