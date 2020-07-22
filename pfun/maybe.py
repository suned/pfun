from abc import ABC, abstractmethod
from functools import wraps
from typing import (Any, Callable, Generic, Iterable, Optional, Sequence,
                    TypeVar, Union, cast)

from .either import Either, Left
from .functions import curry
from .immutable import Immutable
from .list import List
from .monad import Monad, filter_m_, map_m_, sequence_

A = TypeVar('A', covariant=True)
B = TypeVar('B')
C = TypeVar('C')


class Maybe_(Immutable, Monad, ABC):
    """
    Abstract super class for classes that represent computations that can fail.
    Should not be instantiated directly.
    Use `Just` and `Nothing` instead.

    """
    @abstractmethod
    def and_then(self, f: Callable) -> Any:
        """
        Chain together functional calls, carrying along the state of the
        computation that may fail.

        Example:
            >>> f = lambda i: Just(1 / i) if i != 0 else Nothing()
            >>> Just(2).and_then(f)
            Just(0.5)
            >>> Just(0).and_then(f)
            Nothing()

        Args:
            f: the function to call

        Return:
            `Just` wrapping a value of type A if \
            the computation was successful, `Nothing` otherwise.

        """
        raise NotImplementedError()

    @abstractmethod
    def map(self, f: Callable) -> Any:
        """
        Map the result of a possibly failed computation

        Example:
            >>> f = lambda i: Just(1 / i) if i != 0 else Nothing()
            >>> Just(2).and_then(f).map(str)
            Just('0.5')
            >>> Just(0).and_then(f).map(str)
            Nothing()

        Args:
            f: Function to apply to the result

        Return:
            `Just` wrapping result of type B if the computation was

        """
        raise NotImplementedError()

    @abstractmethod
    def or_else(self, default: Any) -> Any:
        """
        Try to get the result of the possibly failed computation if it was
        successful.

        Example:
            >>> Just(1).or_else(2)
            1
            >>> Nothing().or_else(2)
            2

        Args:
            default: Value to return if computation has failed
        Return:
            `value` if this is `Just(value)`, `default_value` if this `Nothing`

        """
        raise NotImplementedError()

    @abstractmethod
    def __bool__(self) -> bool:
        """
        Convert possibly failed computation to a bool

        Example:
            >>> "Just" if Just(1) else "Nothing"
            "Just"
            >>> "Just" if Nothing() else "Nothing"
            "Nothing"


        Return:
            True if this is a `Just` value, \
                 False if this is a `Nothing`

        """
        raise NotImplementedError()


def _invoke_optional_arg(
    f: Union[Callable[[A], B], Callable[[], B]], arg: Optional[A]
) -> B:
    try:
        return f(arg)  # type: ignore
    except TypeError as e:
        if arg is None:
            try:
                return f()  # type: ignore
            except TypeError:
                raise e
        raise


class Just(Maybe_, Generic[A]):
    """
    Represents the result of a successful computation

    """
    get: A
    """
    The result of the computation
    """

    def and_then(self, f: Callable[[A], 'Maybe[B]']) -> 'Maybe[B]':
        return _invoke_optional_arg(f, self.get)

    def map(self, f: Callable[[A], B]) -> 'Maybe[B]':
        return Just(f(self.get))

    def or_else(self, default: B) -> Union[A, B]:
        return self.get

    def __eq__(self, other: Any) -> bool:
        """
        Test if other is a ``Just``

        Args;
            other: Value to compare with
        Return:
            True if other is a ``Just`` and its wrapped value equals the \
        wrapped value of this instance

        """
        if not isinstance(other, Just):
            return False
        return other.get == self.get

    def __repr__(self):
        return f'Just({repr(self.get)})'

    def __bool__(self):
        return True


class Nothing(Maybe_):
    """
    Represents a failed computation

    """
    def and_then(self, f: Callable[[A], 'Maybe[B]']) -> 'Maybe[B]':
        return self

    def __eq__(self, other: Any) -> bool:
        """
        Test if other is a ``Nothing``

        Args:
            other: Value to compare with
        Return:
            True if other is a ``Nothing``, False otherwise

        """
        return isinstance(other, Nothing)

    def __repr__(self) -> str:
        return 'Nothing()'

    def or_else(self, default: B) -> Union[A, B]:
        return default

    def map(self, f: Callable[[Any], B]) -> 'Maybe[B]':
        return self

    def __bool__(self) -> bool:
        return False


Maybe = Union[Nothing, Just[A]]
"""
Type-alias for `Union[Nothing, Just[TypeVar('A')]]`
"""
Maybe.__module__ = __name__


def maybe(f: Callable[..., B]) -> Callable[..., Maybe[B]]:
    """
    Wrap a function that may raise an exception with a `Maybe`.
    Can also be used as a decorator. Useful for turning
    any function into a monadic function

    Example:
        >>> to_int = maybe(int)
        >>> to_int("1")
        Just(1)
        >>> to_int("Whoops")
        Nothing()

    Args:
        f: Function to wrap
    Return:
        f wrapped with a `Maybe`

    """
    @wraps(f)
    def dec(*args, **kwargs):
        try:
            return Just(f(*args, **kwargs))
        except:  # noqa
            return Nothing()

    return dec


def flatten(maybes: Sequence[Maybe[A]]) -> List[A]:
    """
    Extract value from each `Maybe`, ignoring
    elements that are `Nothing`


    Example:
        >>> flatten([Just(1), Nothing(), Just(2)])
        List((1, 2))

    Args:
        maybes: Seqence of `Maybe`
    Return:
        `List` of unwrapped values
    """
    justs = [m for m in maybes if isinstance(m, Just)]
    return List(j.get for j in justs)


@curry
def map_m(f: Callable[[A], Maybe[B]],
          iterable: Iterable[A]) -> Maybe[Iterable[B]]:
    """
    Map each in element in ``iterable`` to
    an `Maybe` by applying ``f``,
    combine the elements by ``and_then``
    from left to right and collect the results

    Example:
        >>> map_m(Just, range(3))
        Just((0, 1, 2))

    Args:
        f: Function to map over ``iterable``
        iterable: Iterable to map ``f`` over
    Return:
        ``f`` mapped over ``iterable`` and combined from left to right.
    """
    return cast(Maybe[Iterable[B]], map_m_(Just, f, iterable))


def sequence(iterable: Iterable[Maybe[A]]) -> Maybe[Iterable[A]]:
    """
    Evaluate each `Maybe` in `iterable` from left to right
    and collect the results

    Example:
        >>> sequence([Just(v) for v in range(3)])
        Just((0, 1, 2))
    Args:
        iterable: The iterable to collect results from
    Return:
        ``Maybe`` of collected results
    """
    return cast(Maybe[Iterable[A]], sequence_(Just, iterable))


@curry
def filter_m(f: Callable[[A], Maybe[bool]],
             iterable: Iterable[A]) -> Maybe[Iterable[A]]:
    """
    Map each element in ``iterable`` by applying ``f``,
    filter the results by the value returned by ``f``
    and combine from left to right.

    Example:
        >>> filter_m(lambda v: Just(v % 2 == 0), range(3))
        Just((0, 2))

    Args:
        f: Function to map ``iterable`` by
        iterable: Iterable to map by ``f``
    Return:
        `iterable` mapped and filtered by `f`
    """
    return cast(Maybe[Iterable[A]], filter_m_(Just, f, iterable))


S = TypeVar('S')
R = TypeVar('R')


def tail_rec(f: Callable[[C], Maybe[Either[C, B]]], a: C) -> Maybe[B]:
    """
    Run a stack safe recursive monadic function `f`
    by calling `f` with `Left` values
    until a `Right` value is produced

    Example:
        >>> from pfun.either import Left, Right, Either
        >>> def f(i: str) -> Maybe[Either[int, str]]:
        ...     if i == 0:
        ...         return Just(Right('Done'))
        ...     return Just(Left(i - 1))
        >>> tail_rec(f, 5000)
        Just('Done')

    Args:
        f: function to run "recursively"
        a: initial argument to `f`
    Return:
        result of `f`
    """
    maybe = f(a)
    if isinstance(maybe, Nothing):
        return maybe
    either = maybe.get
    while isinstance(either, Left):
        maybe = f(either.get)
        if isinstance(maybe, Nothing):
            return maybe
        either = maybe.get
    return Just(either.get)


def from_optional(optional: Optional[A]) -> Maybe[A]:
    """
    Return a possible None value to `Maybe`

    Example:
        >>> from_optional('value')
        Just('value')
        >>> from_optional(None)
        Nothing()

    Args:
        optional: optional value to convert to `Maybe`
    Return:
        `Just(optional)` if `optional` is not `None`, `Nothing` otherwise
    """
    if optional is None:
        return Nothing()
    return Just(optional)


__all__ = [
    'Maybe',
    'Just',
    'Nothing',
    'maybe',
    'flatten',
    'map_m',
    'sequence',
    'filter_m',
    'from_optional'
]
