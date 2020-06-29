from typing import Any, Callable, Generic, Tuple, TypeVar

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
    """
    A Callable that always returns the same value
    regardless of the arguments

    :example:
    >>> f = always(1)
    >>> f(None)
    1
    >>> f('')
    1
    >>> "... and so on..."
    """
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
    """
    Compose functions from left to right

    :example:
    >>> f = lambda v: v * 2
    >>> g = compose(str, f)
    >>> g(3)
    "6"

    :param f: the outermost function in the composition
    :param g: the function to be composed with f
    :param functions: functions to be composed with `f` \
        and `g` from left to right
    :return: `f` composed with `g` composed with `functions` from left to right
    """
    return Composition((f, g) + functions)


def pipeline(
    first: Callable[[Any], Any],
    second: Callable[[Any], Any],
    *rest: Callable[[Any], Any]
):
    """
    Compose functions from right to left

    :example:
    >>> f = lambda v: v * 2
    >>> g = pipeline(f, str)
    >>> g(3)
    "6"

    :param first: the innermost function in the composition
    :param g: the function to compose with f
    :param functions: functions to compose with `first` and \
        `second` from right to left
    :return: `rest` composed from right to left, composed with \
        `second` composed with `first`
    """
    return compose(*reversed(rest), second, first)


__all__ = ['always', 'compose', 'pipeline', 'identity']
