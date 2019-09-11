from typing import TypeVar, Callable, Generic, Tuple, Any

from .immutable import Immutable
from .curry import curry
from functools import reduce

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
    f: Callable[[Any], Any], g: Callable[[Any], Any],
    *functions: Callable[[Any], Any]
) -> Callable[[Any], Any]:
    return Composition((f, g) + functions)  # type: ignore


def pipeline(
    first: Callable[[Any], Any], second: Callable[[Any], Any],
    *rest: Callable[[Any], Any]
):
    return compose(*reversed(rest), second, first)


# Since PEP484 does not support higher-order type variables,
# the functions below cannot be typed here :(
# type versions for each monad is provided
# in their respective namespaces instead (e.g maybe.sequence)


@curry
def sequence_(value, iterable):
    def combine(ms, m):
        return ms.and_then(
            lambda xs: m.and_then(
                lambda x: value(xs + (x, ))
            )
        )  # yapf: disable

    return reduce(combine, iterable, value(()))


@curry
def map_m_(value, f, iterable):
    m_iterable = (f(x) for x in iterable)
    return sequence_(value, m_iterable)


@curry
def filter_m_(value, f, iterable):
    def combine(ms, mbx):
        mb, x = mbx
        return ms.and_then(
            lambda xs: mb.and_then(lambda b: value(xs + (x, ) if b else xs))
        )

    mbs = (f(x) for x in iterable)
    mbxs = zip(mbs, iterable)
    return reduce(combine, mbxs, value(()))

    return result


__all__ = ['always', 'compose', 'pipeline', 'identity']
