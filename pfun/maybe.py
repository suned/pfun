from typing import Generic, TypeVar, Callable, Any, Iterable, cast, Sequence
from functools import wraps

from .immutable import Immutable
from .list import List


A = TypeVar('A')
B = TypeVar('B')


class Maybe(Generic[A], Immutable):
    """
    Abstract super class for classes that represent computations that can fail.
    Should not be instantiated directly. Use :class:`Just` and :class:`Nothing` instead.

    """
    def __init__(self):
        raise TypeError("'Maybe' can't be instantiated directly. Use Just or Nothing.")

    def and_then(self, f: Callable[[A], 'Maybe[B]']) -> 'Maybe[B]':
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

    def map(self, f: Callable[[A], B]) -> 'Maybe[B]':
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

    def __bool__(self):
        """
        Convert possibly failed computation to a bool

        :example:
        >>> "Just" if Just(1) else "Nothing"
        "Just"
        >>> "Just" if Nothing() else "Nothing"
        "Nothing"

        :return: True if this is a :class:`Just` value, False if this is a :class:`Nothing`

        """
        raise NotImplementedError()


class Just(Maybe[A]):
    """
    Subclass of :class:`Maybe` that represents a successful computation

    """
    def __init__(self, a: A):
        """
        Initialize a Just representing a successful computation of result type A

        :param a: Result of the computation

        """
        try:
            super().__init__()
        except:
            pass
        self.a = a

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
        except:
            return Nothing()

    return dec


def flatten(maybes: Sequence[Maybe[A]]) -> List[A]:
    justs = cast(Sequence[Just[A]], [m for m in maybes if m])
    return List(j.a for j in justs)


class Nothing(Maybe[Any]):
    """
    Subclass of :class:`Maybe` that represents a failed computation

    """
    def __init__(self):
        """
        Initialize a value representing a failed computation

        """
        try:
            super().__init__()
        except:
            pass

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
        return self  # type: ignore

    def __bool__(self):
        return False


__all__ = ['Maybe', 'Just', 'Nothing', 'maybe', 'flatten']
