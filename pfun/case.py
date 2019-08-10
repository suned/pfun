from dataclasses import dataclass
from typing import Type, Callable, Union, TypeVar, Generic

from .util import always


class _:
    pass


B = TypeVar('B')
C = TypeVar('C', bound='case')


@dataclass(frozen=True)
class case(Generic[C, B]):
    def __init__(self,
                 t: Union[Type[C], Type[_]],
                 *,
                 then: Callable[[C], B],
                 when: Callable[[C], bool] = always(True)):
        pass


@dataclass(frozen=True)
class BaseCase:
    __caseclass__ = True

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        return dataclass(frozen=True, **kwargs)(cls)

    def match(self, *cases: case[C, B]) -> B:
        pass


class User(BaseCase):
    name: str


class Regular(User):
    pass


class Guest(User):
    pass
