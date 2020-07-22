from __future__ import annotations

from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable, Generic, Iterable, TypeVar, Union, cast

from .functions import curry
from .immutable import Immutable
from .monad import Monad, filter_m_, map_m_, sequence_

A = TypeVar('A', covariant=True)
B = TypeVar('B', covariant=True)
C = TypeVar('C')
D = TypeVar('D')


class Either_(Immutable, Monad, ABC):
    """
    Abstract class representing a computation with either
    ``A`` or ``B`` as its result.
    Should not be instantiated directly,
    use `Left` or `Right` instead
    """
    @abstractmethod
    def and_then(self, f):
        """
        Chain together functions of either computations, keeping
        track of whether or not any of them have failed

        Example:
            >>> f = lambda i: Right(1 / i) if i != 0 else Left('i was 0')
            >>> Right(1).and_then(f)
            Right(1.0)
            >>> Right(0).and_then(f)
            Left('i was 0')

        Args:
            f: The function to call
        Return:
            `Right` of type A if \
            the computation was successful, `Left` of type B otherwise.
        """
        raise NotImplementedError()

    @abstractmethod
    def __bool__(self) -> bool:
        """
        Convert this result to a boolean value

        Example:
            >>> "Right" if Right(1) else "Left"
            "Right"
            >>> "Right" if Left("an error") else "Left"
            "Left"


        Return:
            True if this as an `Right`,
            False if this is an `Left`
        """
        raise NotImplementedError()

    @abstractmethod
    def or_else(self, default):
        """
        Try to get the result of this either computation, return default
        if this is a ``Left`` value

        Example:
            >>> Right(1).or_else(2)
            1
            >>> Left(1).or_else(2)
            2

        Args:
            default: Value to return if this is a ``Left`` value
        Return:
            Result of computation if this is a ``Right`` value, \
            default otherwise
        """
        raise NotImplementedError()

    @abstractmethod
    def map(self, f):
        """
        Map the result of this either computation

        Example:
            >>> f = (lambda i: Right(1 / i)
            ...                if i != 0 else Left('i was 0').map(str))
            >>> Right(1).and_then(f).map(str)
            Right('0.5')
            >>> Ok(0).and_then(f).map(str)
            Left('i was 0')

        Args:
            f: Function to apply to the result
        Return:
            `Right` wrapping result of type C  \
            if the computation was if this is a ``Right`` value, \
            `Left` of type B otherwise

    """
        raise NotImplementedError()


class Right(Either_, Generic[A]):
    """
    Represents the ``Right`` case of ``Either``
    """
    get: A
    """
    The right result
    """

    def or_else(self, default: C) -> A:
        return self.get

    def map(self, f: Callable[[A], C]) -> Either[Any, C]:
        return Right(f(self.get))

    def and_then(self, f: Callable[[A], Either[B, C]]) -> Either[B, C]:
        return f(self.get)

    def __eq__(self, other: Any) -> bool:
        """
        Test if ``other`` is a `Right` wrapping the same value as
        this instance

        Example:
            >>> Right('value') == Right('value')
            True
            >>> Right('another value') == Right('value')
            False

        Args:
            other: object to compare with
        Return:
            True if other is a `Right` instance and wraps the same \
            value as this instance, False otherwise
        """
        return isinstance(other, Right) and self.get == other.get

    def __bool__(self) -> bool:
        return True

    def __repr__(self):
        return f'Right({repr(self.get)})'


class Left(Either_, Generic[B]):
    """
    Represents the ``Left`` case of ``Either``
    """
    get: B
    """
    The left result
    """

    def or_else(self, default: C) -> C:
        return default

    def map(self, f: Callable[[A], C]) -> Either[B, C]:
        return self

    def __eq__(self, other: object) -> bool:
        """
        Test if ``other`` is an `Left` wrapping the same value as
        this instance

        Example:
            >>> Left('error message') == Left('error message')
            True
            >>> Left('error message') == Left('another message')
            False

        Args:
            other: object to compare with
        Return:
            True if other is an `Left` instance and wraps the same \
            value as this instance, False otherwise
        """
        return isinstance(other, Left) and other.get == self.get

    def __bool__(self) -> bool:
        return False

    def and_then(self, f: Callable[[A], Either[B, C]]) -> Either[B, C]:
        return self

    def __repr__(self):
        return f'Left({repr(self.get)})'


Either = Union[Left[B], Right[A]]
"""
Type-alias for `Union[Left[TypeVar('L')], Right[TypeVar('R')]]`
"""
Either.__module__ = __name__


def either(f: Callable[..., A]) -> Callable[..., Either[A, B]]:
    """
    Turn ``f`` into a monadic function in the ``Either`` monad by wrapping
    in it a `Right`

    Example:
        >>> either(lambda v: v)(1)
        Right(1)

    Args:
        f: function to wrap
    Return:
        ``f`` wrapped with a ``Right``
    """
    @wraps(f)
    def decorator(*args, **kwargs):
        return Right(f(*args, **kwargs))

    return decorator


def sequence(iterable: Iterable[Either[A, B]]) -> Either[Iterable[A], B]:
    """
    Evaluate each ``Either`` in `iterable` from left to right
    and collect the results

    Example:
        >>> sequence([Right(v) for v in range(3)])
        Right((0, 1, 2))

    Args:
        iterable: The iterable to collect results from
    Return:
        ``Either`` of collected results
    """
    return cast(Either[Iterable[A], B], sequence_(Right, iterable))


@curry
def map_m(f: Callable[[A], Either[B, C]],
          iterable: Iterable[A]) -> Either[Iterable[B], C]:
    """
    Map each in element in ``iterable`` to
    an `Either` by applying ``f``,
    combine the elements by ``and_then``
    from left to right and collect the results

    Example:
        >>> map_m(Right, range(3))
        Right((0, 1, 2))

    Args:
        f: Function to map over ``iterable``
        iterable: Iterable to map ``f`` over
    Return:
         ``f`` mapped over ``iterable`` and combined from left to right.
    """
    return cast(Either[Iterable[B], C], map_m_(Right, f, iterable))


@curry
def filter_m(f: Callable[[A], Either[bool, B]],
             iterable: Iterable[A]) -> Either[Iterable[A], B]:
    """
    Map each element in ``iterable`` by applying ``f``,
    filter the results by the value returned by ``f``
    and combine from left to right.

    Example:
        >>> filter_m(lambda v: Right(v % 2 == 0), range(3))
        Right((0, 2))

    Args:
        f: Function to map ``iterable`` by
        iterable: Iterable to map by ``f``
    Return:
        `iterable` mapped and filtered by `f`
    """
    return cast(Either[Iterable[A], B], filter_m_(Right, f, iterable))


def tail_rec(f: Callable[[D], Either[C, Either[D, B]]], a: D) -> Either[C, B]:
    """
    Run a stack safe recursive monadic function `f`
    by calling `f` with `Left` values
    until a `Right` value is produced

    Example:
        >>> def f(i: str) -> Either[Either[int, str]]:
        ...     if i == 0:
        ...         return Right(Right('Done'))
        ...     return Right(Left(i - 1))
        >>> tail_rec(f, 5000)
        Right('Done')

    Args:
        f: function to run "recursively"
        a: initial argument to `f`
    Return:
        result of `f`
    """
    outer_either = f(a)
    if isinstance(outer_either, Left):
        return outer_either
    inner_either = outer_either.get
    while isinstance(inner_either, Left):
        outer_either = f(inner_either.get)
        if isinstance(outer_either, Left):
            return outer_either
        inner_either = outer_either.get
    return inner_either


def catch(f: Callable[..., A]) -> Callable[..., Either[Exception, A]]:
    """
    Decorator that wraps return values of decoratod functions with `Right`,
    and wraps catched exceptions with `Left`

    Example:
        >>> catch_division = catch(lambda v: 1 / v)
        >>> catch_division(1)
        Right(1.0)
        >>> catch_division(0)
        Left(ZeroDivisionError('division by zero'))

    Args:
        f: function to decorate
    Return:
        decorated function
    """
    @wraps(f)
    def decorator(*args, **kwargs) -> Either[Exception, A]:
        try:
            return Right(f(*args, **kwargs))
        except Exception as e:
            return Left(e)

    return decorator


__all__ = [
    'Either',
    'Left',
    'Right',
    'either',
    'map_m',
    'sequence',
    'filter_m',
    'catch'
]
