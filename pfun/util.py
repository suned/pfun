from typing import TypeVar, Callable, Generic, Tuple, Any

from .immutable import Immutable

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


def compose(
    f: Callable[[Any], Any],
    g: Callable[[Any], Any],
    *functions: Callable[[Any], Any]
) -> Callable[[Any], Any]:
    return Composition((f, g) + functions)  # type: ignore


def pipeline(
    first: Callable[[Any], Any],
    second: Callable[[Any], Any],
    *rest: Callable[[Any], Any]
):
    return compose(*reversed(rest), second, first)  # type: ignore


__all__ = ['always', 'compose', 'pipeline', 'identity']
