from typing import TypeVar, Callable, Generic, Tuple, Any

from .immutable import Immutable
from .curry import curry

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


# Since mypy does not support higher-order type variables,
# the functions below cannot be typed :(


@curry
def sequence_(value, iterable):
    result = value(())
    for m in iterable:
        result = result.and_then(
            lambda xs: m.and_then(
                lambda x: value(xs + (x, ))
            )
        )  # yapf: disable
    return result


@curry
def map_m_(value, f, iterable):
    m_iterable = (f(x) for x in iterable)
    return sequence_(value, m_iterable)


@curry
def filter_m_(value, f, iterable):
    result = value(())
    for x in iterable:
        result = result.and_then(
            lambda xs: f(x).and_then(
                lambda b: value(xs + (x, )) if b else value(xs)
            )
        )  # yapf: disable
    return result


__all__ = ['always', 'compose', 'pipeline', 'identity']
