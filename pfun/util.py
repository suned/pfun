from typing import TypeVar, Callable, Generic, Tuple

from .immutable import Immutable
from .list import List

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')


def identity(v: A) -> A:
    """
    The identity function. Just gives back its argument

    :example:
    >>> identity('value')
    'value'

    :param v: The value to get back
    :return: v
    """
    return v


Unary = Callable[[A], B]
Predicate = Callable[[A], bool]


class always(Generic[A], Immutable):
    value: A

    def __call__(self, *args, **kwargs) -> A:
        return self.value


class Composition(Immutable):
    functions: Tuple[Callable, ...]

    def __call__(self, *args, **kwargs):
        fs = reversed(self.functions)
        first, *rest = fs
        last_result = first(*args, **kwargs)
        for f in rest:
            last_result = f(last_result)
        return last_result


def compose(*functions: Callable) -> Callable:
    return Composition(functions)
