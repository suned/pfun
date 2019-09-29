from typing import (Generic, TypeVar, Callable, Any, Sequence, Iterable, cast)
from functools import wraps
from abc import ABC, abstractmethod

from .immutable import Immutable
from .list import List
from .curry import curry
from .monad import Monad, map_m_, sequence_, filter_m_

A = TypeVar('A')
B = TypeVar('B')


class Maybe(Generic[A], Immutable, Monad, ABC):
    """
    Represents computations that can fail.
    """
    @abstractmethod
    def and_then(self, f: Callable[[A], 'Maybe[B]']) -> 'Maybe[B]':
        """
        Chain together functions that may fail

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
    def map(self, f: Callable[[A], B]) -> 'Maybe[B]':
        """
        Map the result of a possibly failed function

        :example:
        >>> f = lambda i: Just(1 / i) if i != 0 else Nothing()
        >>> Just(2).and_then(f).map(str)
        Just('0.5')
        >>> Just(0).and_then(f).map(str)
        Nothing()

        :param f: Function to apply to the result
        :return: :class:`Maybe` mapped by ``f``

        """
        raise NotImplementedError()

    @abstractmethod
    def or_else(self, default: A) -> A:
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
        Convert this :clas:`Maybe` to a bool

        :example:
        >>> "Just" if Just(1) else "Nothing"
        "Just"
        >>> "Just" if Nothing() else "Nothing"
        "Nothing"

        :return: True if this is a :class:`Just` value,
                 False if this is a :class:`Nothing`

        """
        raise NotImplementedError()

    @property
    def get(self) -> A:
        """
        Get the value wrapped by this :class:`Maybe`. \
            Fails if this is a :class:`Nothing`

        :return: [description]
        """
        raise NotImplementedError()


class Just(Maybe[A]):
    """
    Represents a successful computation

    """
    a: A

    @property
    def get(self) -> A:
        return self.a

    def and_then(self, f: Callable[[A], 'Maybe[B]']) -> 'Maybe[B]':
        return f(self.a)

    def map(self, f: Callable[[A], B]) -> 'Maybe[B]':
        return Just(f(self.a))

    def or_else(self, default: A) -> A:
        return self.a

    def __eq__(self, other: Any) -> bool:
        """
        Test if other is a ``Just``

        :param other: Value to compare with
        :return: True if other is a ``Just`` and its wrapped value equals the \
        wrapped value of this instance

        """
        if not isinstance(other, Just):
            return False
        return other.a == self.a

    def __repr__(self):
        return f'Just({repr(self.a)})'

    def __bool__(self):
        return True


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


class Nothing(Maybe[Any]):
    """
    Represents a failed computation

    """
    @property
    def get(self):
        raise AttributeError('"Nothing" does not support "get"')

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


def flatten(maybes: Sequence[Maybe[A]]) -> List[A]:
    """
    Extract value from each :class:`Maybe`, ignoring
    elements that are :class:`Nothing`

    :param maybes: Seqence of :class:`Maybe`
    :return: :class:`List` of unwrapped values
    :rtype: List[A]
    """
    justs = [m for m in maybes if m]
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
    :returns: ``Maybe`` of collected results
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
    :return:
    """
    return cast(Maybe[Iterable[A]], filter_m_(Just, f, iterable))


__all__ = [
    'Maybe',
    'Just',
    'Nothing',
    'maybe',
    'flatten',
    'map_m',
    'sequence',
    'filter_m'
]
