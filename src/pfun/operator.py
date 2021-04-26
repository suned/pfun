import operator
from typing import Container, TypeVar, overload

from . import protocols
from .functions import Unary, curry

A = TypeVar('A')
B = TypeVar('B')


@curry
def add(a: protocols.SupportsAdd[A, B], b: A) -> B:
    return a + b


@overload
def and_(a: protocols.SupportsBool) -> Unary[protocols.SupportsBool, bool]:
    ...


@overload
def and_(a: protocols.SupportsAnd[A, B]) -> Unary[A, B]:
    ...


def and_(a) -> Unary:
    return curry(operator.and_)(a)


@curry
def contains(a: Container[A], b: A) -> bool:
    return b in a


@curry
def countOf(a: Container[A], b: A) -> int:
    return operator.countOf(a, b)


@curry
def delitem(a: protocols.SupportsDelItem[A], b: A) -> None:
    del a[b]


attrgetter = operator.attrgetter
concat = curry(operator.concat)
