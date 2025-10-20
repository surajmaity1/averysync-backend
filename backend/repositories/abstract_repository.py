from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel


T = TypeVar('T', bound = BaseModel)


class AbstractRepository(ABC, Generic[T]):
    @abstractmethod
    def get_by_id(self, id: str) -> Optional[T]:
        pass


class AbstractUserRepository(AbstractRepository[T]):
    pass