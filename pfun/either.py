from typing import Generic, TypeVar, Callable, Any, Iterable, cast
from functools import wraps
from abc import ABC, abstractmethod

from .immutable import Immutable
from .monad import Monad, sequence_, map_m_, filter_m_
from .curry import curry

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')


class Either(Generic[B, A], Immutable, Monad, ABC):
    """
    Abstract class representing a computation with either
    ``A`` or ``B`` as its result.
    Should not be instantiated directly,
    use :class:`Left` or :class:`Right` instead
    """
    @abstractmethod
    def and_then(self, f: Callable[[A], 'Either[B, C]']) -> 'Either[B, C]':
        """
        Chain together functions of either computations, keeping
        track of whether or not any of them have failed

        :example:
        >>> f = lambda i: Right(1 / i) if i != 0 else Left('i was 0')
        >>> Right(1).and_then(f)
        Right(1.0)
        >>> Right(0).and_then(f)
        Left('i was 0')

        :param f: The function to call
        :return: :class:`Right` of type A if \
        the computation was successful, :class:`Left` of type B otherwise.
        """
        raise NotImplementedError()

    @abstractmethod
    def __bool__(self):
        """
        Convert this result to a boolean value

        :example:
        >>> "Right" if Right(1) else "Left"
        "Right"
        >>> "Right" if Left("an error") else "Left"
        "Left"

        :return: True if this as an :class:`Right`,
                 False if this is an :class:`Left`
        """
        raise NotImplementedError()

    @abstractmethod
    def or_else(self, default: A) -> A:
        """
        Try to get the result of this either computation, return default
        if this is a ``Left`` value

        :example:
        >>> Right(1).or_else(2)
        1
        >>> Left(1).or_else(2)
        2

        :param default: Value to return if this is a ``Left`` value
        :return: Result of computation if this is a ``Right`` value, \
                 default otherwise
        """
        raise NotImplementedError()

    @abstractmethod
    def map(self, f: Callable[[A], C]) -> 'Either[B, C]':
        """
        Map the result of this either computation

        :example:
        >>> f = lambda i: Right(1 / i) if i != 0 else Left('i was 0').map(str)
        >>> Right(1).and_then(f).map(str)
        Right('0.5')
        >>> Ok(0).and_then(f).map(str)
        Left('i was 0')

        :param f: Function to apply to the result
        :return: :class:`Right` wrapping result of type C  \
                 if the computation was if this is a ``Right`` value, \
                 :class:`Left` of type B otherwise

    """
        raise NotImplementedError()


class Right(Either[B, A]):
    """
    Represents one of the ``Right`` case of ``Either``
    """
    a: A

    def or_else(self, default: A) -> A:
        return self.a

    def map(self, f: Callable[[A], C]) -> Either[B, C]:
        return Right(f(self.a))

    def and_then(self, f):
        return f(self.a)

    def __eq__(self, other: Any) -> bool:
        """
        Test if ``other`` is a :class:`Right` wrapping the same value as
        this instance

        :example:
        >>> Right('value') == Right('value')
        True
        >>> Right('another value') == Right('value')
        False

        :param other: object to compare with
        :return: True if other is a :class:`Right`
                 instance and wraps the same \
        value as this instance, False otherwise
        """
        return isinstance(other, Right) and self.a == other.a

    def __bool__(self) -> bool:
        return True

    def __repr__(self):
        return f'Right({repr(self.a)})'


class Left(Either[B, A]):
    b: B

    def or_else(self, default: A) -> A:
        return default

    def map(self, f: Callable[[A], C]) -> Either[B, C]:
        return self  # type: ignore

    def __eq__(self, other: object) -> bool:
        """
        Test if ``other`` is an :class:`Left` wrapping the same value as
        this instance

        :example:
        >>> Left('error message') == Left('error message')
        True
        >>> Left('error message') == Left('another message')
        False

        :param other: object to compare with
        :return: True if other is an :class:`Left` instance and wraps the same
        value as this instance, False otherwise
        """
        return isinstance(other, Left) and other.b == self.b

    def __bool__(self) -> bool:
        return False

    def and_then(self, f: Callable[[A], Either[B, C]]) -> Either[B, C]:
        return self  # type: ignore

    def __repr__(self):
        return f'Left({repr(self.b)})'


def either(f: Callable[..., A]) -> Callable[..., Either[A, B]]:
    """

    """
    @wraps(f)
    def decorator(*args, **kwargs):
        return Left(f(*args, **kwargs))

    return decorator


def sequence(iterable: Iterable[Either[A, B]]) -> Either[Iterable[A], B]:
    return cast(Either[Iterable[A], B], sequence_(Left, iterable))


@curry
def map_m(f: Callable[[A], Either[B, C]],
          iterable: Iterable[A]) -> Either[Iterable[B], C]:
    return cast(Either[Iterable[B], C], map_m_(Left, f, iterable))


@curry
def filter_m(f: Callable[[A], Either[bool, B]],
             iterable: Iterable[A]) -> Either[Iterable[A], B]:
    return cast(Either[Iterable[A], B], filter_m_(Left, f, iterable))


__all__ = [
    'Either', 'Left', 'Right', 'either', 'map_m', 'sequence', 'filter_m'
]
