from typing import TypeVar

from typing_extensions import Protocol

A = TypeVar('A', contravariant=True)
B = TypeVar('B', covariant=True)


class SupportsCall(Protocol[A, B]):
    def __call__(self, a: A) -> B:
        pass


class SupportsLt(Protocol[A, B]):
    def __lt__(self, other: A) -> B:
        pass


class SupportsLe(Protocol[A, B]):
    def __le__(self, other: A) -> B:
        pass


class SupportsEq(Protocol[B]):
    def __eq__(self, other: object) -> bool:
        pass


class SupportsNe(Protocol[B]):
    def __ne__(self, other: object) -> bool:
        pass


class SupportsAdd(Protocol[A, B]):
    def __add__(self, other: A) -> B:
        pass


class SupportsAnd(Protocol[A, B]):
    def __and__(self, other: A) -> B:
        pass


class SupportsBool(Protocol):
    def __bool__(self) -> bool:
        pass


class SupportsIndex(Protocol[A, B]):
    def __index__(self, element: A) -> B:
        pass


class SupportsDelItem(Protocol[A]):
    def __delitem__(self, item: A) -> None:
        pass
