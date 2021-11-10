import functools
import inspect
from typing import Any, Callable, Generic, Tuple, TypeVar

from .immutable import Immutable

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')


def identity(v: A) -> A:
    """
    The identity function. Just gives back its argument

    Example:
        >>> identity('value')
        'value'

    Args:
        v: The value to get back

    Return:
        `v`
    """
    return v


Unary = Callable[[A], B]
Predicate = Callable[[A], bool]


class Always(Generic[A], Immutable):
    """
    A Callable that always returns the same value
    regardless of the arguments

    Example:
        >>> f = Always(1)
        >>> f(None)
        1
        >>> f('')
        1
        >>> "... and so on..."

    """
    value: A

    def __call__(self, *args: object, **kwargs: object) -> A:
        return self.value


def always(value: A) -> Callable[..., A]:
    """
    Get a function that always returns `value`

    Example:
        >>> f = always(1)
        >>> f(None)
        1
        >>> f('')
        1
        >>> "... and so on..."

    Args:
        value: The value to return always

    Return:
        function that always returns `value`
    """
    return Always(value)


class Composition(Immutable):
    functions: Tuple[Callable, ...]

    def __repr__(self) -> str:
        functions_repr = ', '.join(repr(f) for f in self.functions)
        return f'compose({functions_repr})'

    def __call__(self, *args: object, **kwargs: object) -> Any:
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

    Example:
        >>> f = lambda v: v * 2
        >>> g = compose(str, f)
        >>> g(3)
        "6"

    Args:
        f: the outermost function in the composition
        g: the function to be composed with f
        functions: functions to be composed with `f` \
        and `g` from left to right

    Return:
        `f` composed with `g` composed with `functions` from left to right
    """
    fs: Tuple[Callable, ...] = ()
    for h in (f, g) + functions:
        if isinstance(h, Composition):
            fs += h.functions
        else:
            fs += (h,)
    return Composition(fs)


def pipeline(
    first: Callable[[Any], Any],
    second: Callable[[Any], Any],
    *rest: Callable[[Any], Any]
) -> Callable[[Any], Any]:
    """
    Compose functions from right to left

    Example:
        >>> f = lambda v: v * 2
        >>> g = pipeline(f, str)
        >>> g(3)
        "6"

    Args:
        first: the innermost function in the composition
        second: The second-innermost function in the composition
        rest: functions to compose with `first` and \
        `second` from right to left

    Return:
        `rest` composed from right to left, composed with \
            `second` composed with `first`
    """
    return compose(*reversed(rest), second, first)


class Curry:
    _f: Callable

    def __init__(self, f: Callable):
        functools.wraps(f)(self)
        self._f = f  # type: ignore

    def __repr__(self) -> str:
        return f'curry({repr(self._f)})'

    def __call__(self, *args: object, **kwargs: object) -> Any:
        signature = inspect.signature(self._f)
        bound = signature.bind_partial(*args, **kwargs)
        bound.apply_defaults()
        arg_names = {a for a in bound.arguments.keys()}
        parameters = {p for p in signature.parameters.keys()}
        if parameters - arg_names == set():
            return self._f(*args, **kwargs)
        if isinstance(self._f, functools.partial):
            partial = functools.partial(
                self._f.func,
                *(self._f.args + args),
                **self._f.keywords,
                **kwargs
            )
        else:
            partial = functools.partial(self._f, *args, **kwargs)
        return Curry(partial)


def curry(f: Callable) -> Callable:
    """
    Get a version of ``f`` that can be partially applied

    Example:
        >>> f = lambda a, b: a + b
        >>> f_curried = curry(f)
        >>> f_curried(1)
        functools.partial(<function <lambda> at 0x1051f0950>, a=1)
        >>> f_curried(1)(1)
        2

    Args:
        f: The function to curry
    Returns:
        Curried version of ``f``
    """
    @functools.wraps(f)
    def decorator(*args: object, **kwargs: object) -> Any:
        return Curry(f)(*args, **kwargs)

    return decorator


def flip(f: Callable) -> Callable:
    """
    Reverse the order of positional arguments of `f`

    Example:
        >>> f = lambda a, b, c: (a, b, c)
        >>> flip(f)('a', 'b', 'c')
        ('c', 'b', 'a')

    Args:
        f: Function to flip positional arguments of
    Returns:
        Function with positional arguments flipped
    """
    return curry(lambda *args, **kwargs: f(*reversed(args), **kwargs))


__all__ = [
    'curry', 'always', 'compose', 'pipeline', 'identity', 'Unary', 'Predicate'
]
