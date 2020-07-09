from abc import ABC, abstractmethod
from functools import wraps
from typing import (Any, Callable, Generator, Generic, Iterable, Optional,
                    Sequence, TypeVar, Union, cast)

from .curry import curry
from .either import Either, Left
from .immutable import Immutable
from .list import List
from .monad import Monad, filter_m_, map_m_, sequence_
from .with_effect import with_effect_tail_rec

A = TypeVar('A')
B = TypeVar('B')


class Maybe_(Immutable, Monad, ABC):
    """
    Abstract super class for classes that represent computations that can fail.
    Should not be instantiated directly.
    Use :class:`Just` and :class:`Nothing` instead.

    """
    @abstractmethod
    def and_then(self, f):
        """
        Chain together functional calls, carrying along the state of the
        computation that may fail.

        :example:
        >>> f = lambda i: Just(1 / i) if i != 0 else Nothing()
        >>> Just(2).and_then(f)
        Just(0.5)
        >>> Just(0).and_then(f)
        Nothing()

        :param f: the function to call
        :return: :class:`Just` wrapping a value of type A if \
        the computation was successful, :class:`Nothing` otherwise.

        """
        raise NotImplementedError()

    @abstractmethod
    def map(self, f):
        """
        Map the result of a possibly failed computation

        :example:
        >>> f = lambda i: Just(1 / i) if i != 0 else Nothing()
        >>> Just(2).and_then(f).map(str)
        Just('0.5')
        >>> Just(0).and_then(f).map(str)
        Nothing()

        :param f: Function to apply to the result
        :return: :class:`Just` wrapping result of type B if the computation was

        """
        raise NotImplementedError()

    @abstractmethod
    def or_else(self, default):
        """
        Try to get the result of the possibly failed computation if it was
        successful.

        :example:
        >>> Just(1).or_else(2)
        1
        >>> Nothing().or_else(2)
        2

        :param default: Value to return if computation has failed
        :return: Default value

        """
        raise NotImplementedError()

    @abstractmethod
    def __bool__(self):
        """
        Convert possibly failed computation to a bool

        :example:
        >>> "Just" if Just(1) else "Nothing"
        "Just"
        >>> "Just" if Nothing() else "Nothing"
        "Nothing"

        :return: True if this is a :class:`Just` value,
                 False if this is a :class:`Nothing`

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
    Subclass of :class:`Maybe` that represents a successful computation

    """
    get: A

    def and_then(self, f: Callable[[A], 'Maybe[B]']) -> 'Maybe[B]':
        return _invoke_optional_arg(f, self.get)

    def map(self, f: Callable[[A], B]) -> 'Maybe[B]':
        return Just(f(self.get))

    def or_else(self, default: A) -> A:
        return self.get

    def __eq__(self, other: Any) -> bool:
        """
        Test if other is a ``Just``

        :param other: Value to compare with
        :return: True if other is a ``Just`` and its wrapped value equals the \
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
    Subclass of :class:`Maybe` that represents a failed computation

    """
    def and_then(self, f: Callable[[A], 'Maybe[B]']) -> 'Maybe[B]':
        return self

    def __eq__(self, other: Any) -> bool:
        """
        Test if other is a ``Nothing``

        :param other: Value to compare with
        :return: True if other is a ``Nothing``, False otherwise

        """
        return isinstance(other, Nothing)

    def __repr__(self):
        return 'Nothing()'

    def or_else(self, default: A) -> A:
        return default

    def map(self, f: Callable[[Any], B]) -> 'Maybe[B]':
        return self

    def __bool__(self):
        return False


Maybe = Union[Nothing, Just[A]]


def maybe(f: Callable[..., B]) -> Callable[..., Maybe[B]]:
    """
    Wrap a function that may raise an exception with a :class:`Maybe`.
    Can also be used as a decorator. Useful for turning
    any function into a monadic function

    :example:
    >>> to_int = maybe(int)
    >>> to_int("1")
    Just(1)
    >>> to_int("Whoops")
    Nothing()

    :param f: Function to wrap
    :return: f wrapped with a :class:`Maybe`

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
    Extract value from each :class:`Maybe`, ignoring
    elements that are :class:`Nothing`

    :param maybes: Seqence of :class:`Maybe`
    :return: :class:`List` of unwrapped values
    """
    justs = [m for m in maybes if isinstance(m, Just)]
    return List(j.get for j in justs)


@curry
def map_m(f: Callable[[A], Maybe[B]],
          iterable: Iterable[A]) -> Maybe[Iterable[B]]:
    """
    Map each in element in ``iterable`` to
    an :class:`Maybe` by applying ``f``,
    combine the elements by ``and_then``
    from left to right and collect the results

    :example:
    >>> map_m(Just, range(3))
    Just((0, 1, 2))

    :param f: Function to map over ``iterable``
    :param iterable: Iterable to map ``f`` over
    :return: ``f`` mapped over ``iterable`` and combined from left to right.
    """
    return cast(Maybe[Iterable[B]], map_m_(Just, f, iterable))


def sequence(iterable: Iterable[Maybe[A]]) -> Maybe[Iterable[A]]:
    """
    Evaluate each :class:`Maybe` in `iterable` from left to right
    and collect the results

    :example:
    >>> sequence([Just(v) for v in range(3)])
    Just((0, 1, 2))

    :param iterable: The iterable to collect results from
    :return: ``Maybe`` of collected results
    """
    return cast(Maybe[Iterable[A]], sequence_(Just, iterable))


@curry
def filter_m(f: Callable[[A], Maybe[bool]],
             iterable: Iterable[A]) -> Maybe[Iterable[A]]:
    """
    Map each element in ``iterable`` by applying ``f``,
    filter the results by the value returned by ``f``
    and combine from left to right.

    :example:
    >>> filter_m(lambda v: Just(v % 2 == 0), range(3))
    Just((0, 2))

    :param f: Function to map ``iterable`` by
    :param iterable: Iterable to map by ``f``
    :return: `iterable` mapped and filtered by `f`
    """
    return cast(Maybe[Iterable[A]], filter_m_(Just, f, iterable))


S = TypeVar('S')
R = TypeVar('R')
Maybes = Generator[Maybe[S], S, R]


def with_effect(f: Callable[..., Maybes[Any, R]]) -> Callable[..., Maybe[R]]:
    """
    Decorator for functions that
    return a generator of maybes and a final result.
    Iteraters over the yielded maybes and sends back the
    unwrapped values using "and_then"

    :example:
    >>> @with_effect
    ... def f() -> Maybes[int, int]:
    ...     a = yield Just(2)
    ...     b = yield Just(2)
    ...     return a + b
    >>> f()
    Just(4)

    :param f: generator function to decorate
    :return: `f` decorated such that generated :class:`Maybe` \
        will be chained together with `and_then`
    """
    return with_effect_tail_rec(Just, f, tail_rec)


def tail_rec(f: Callable[[A], Maybe[Either[A, B]]], a: A) -> Maybe[B]:
    """
    Run a stack safe recursive monadic function `f`
    by calling `f` with :class:`Left` values
    until a :class:`Right` value is produced

    :example:
    >>> from pfun.either import Left, Right, Either
    >>> def f(i: str) -> Maybe[Either[int, str]]:
    ...     if i == 0:
    ...         return Just(Right('Done'))
    ...     return Just(Left(i - 1))
    >>> tail_rec(f, 5000)
    Just('Done')

    :param f: function to run "recursively"
    :param a: initial argument to `f`
    :return: result of `f`
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

    :example:
    >>> from_optional('value')
    Just('value')
    >>> from_optional(None)
    Nothing()

    :param optional: optional value to convert to `Maybe`
    :return: `Just(optional)` if `optional` is not `None`, `Nothing` otherwise
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
    'with_effect',
    'Maybes',
    'from_optional'
]
