from typing import TypeVar, overload, Container
import operator
from .curry import curry

from . import protocol
from .util import Unary

A = TypeVar('A')
B = TypeVar('B')


@curry
def add(a: protocol.SupportsAdd[A, B], b: A) -> B:
    return a + b


@overload
def and_(a: protocol.SupportsBool) -> Unary[protocol.SupportsBool, bool]:
    ...


@overload
def and_(a: protocol.SupportsAnd[A, B]) -> Unary[A, B]:
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
def delitem(a: protocol.SupportsDelItem[A], b: A) -> None:
    del a[b]


attrgetter = operator.attrgetter
concat = curry(operator.concat)
