from typing import Protocol, TypeVar

A = TypeVar('A', contravariant=True)
B = TypeVar('B', covariant=True)


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
