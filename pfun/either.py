from typing import Generic, TypeVar, Callable, Any, Iterable, cast
from functools import wraps
from abc import ABC, abstractmethod

from .immutable import Immutable
from .monad import Monad, sequence_, map_m_, filter_m_
from .curry import curry

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')


class Either(Generic[A, B], Immutable, Monad, ABC):
    """
    Abstract class representing a potentially failed computation.
    Should not be instantiated directly,
    use :class:`Ok` or :class:`Error` instead
    """
    @abstractmethod
    def and_then(self, f: Callable[[A], 'Either[A, B]']) -> 'Either[A, B]':
        """
        Chain together functions of potentially failed computations, keeping
        track of whether or not any of them have failed

        :example:
        >>> f = lambda i: Ok(1 / i) if i != 0 else Error('i was 0')
        >>> Ok(1).and_then(f)
        Ok(1.0)
        >>> Ok(0).and_then(f)
        Error('i was 0')

        :param f: The function to call
        :return: :class:`Ok` of type A if \
        the computation was successful, :class:`Error` of type B otherwise.
        """
        raise NotImplementedError()

    @abstractmethod
    def __bool__(self):
        """
        Convert this result to a boolean value

        :example:
        >>> "Ok" if Ok(1) else "Error"
        "Ok"
        >>> "Ok" if Error("an error") else "Error"
        "Error"

        :return: True if this as an :class:`Ok`,
                 False if this is an :class:`Error`
        """
        raise NotImplementedError()

    @abstractmethod
    def or_else(self, default: A) -> A:
        """
        Try to get the result of possibly failed computation, return default
        if the computation has failed

        :example:
        >>> Ok(1).or_else(2)
        1
        >>> Error(1).or_else(2)
        2

        :param default: Value to return if the computation has failed
        :return: Result of computation if it was successful, default otherwise
        """
        raise NotImplementedError()

    @abstractmethod
    def map(self, f: Callable[[A], C]) -> 'Either[C, B]':
        """
        Map the result of a possibly failed computation

        :example:
        >>> f = lambda i: Ok(1 / i) if i != 0 else Error('i was 0').map(str)
        >>> Ok(1).and_then(f).map(str)
        Ok('0.5')
        >>> Ok(0).and_then(f).map(str)
        Error('i was 0')

        :param f: Function to apply to the result
        :return: :class:`Ok` wrapping result of type C if the computation was \
        successful, :class:`Error` of type B otherwise

    """
        raise NotImplementedError()


class Left(Either[A, B]):
    """
    Represents a successful computation of type A
    """
    a: A

    def or_else(self, default: A) -> A:
        return self.a

    def map(self, f):
        return Left(f(self.a))

    def and_then(self, f):
        return f(self.a)

    def __eq__(self, other: Any) -> bool:
        """
        Test if ``other`` is an :class:`Ok` wrapping the same value as
        this instance

        :example:
        >>> Ok('value') == Ok('value')
        True
        >>> Ok('another value') == Ok('value')
        False

        :param other: object to compare with
        :return: True if other is an :class:`Ok` instance and wraps the same \
        value as this instance, False otherwise
        """
        return isinstance(other, Left) and self.a == other.a

    def __bool__(self) -> bool:
        return False

    def __repr__(self):
        return f'Left({repr(self.a)})'


class Right(Either[A, B]):
    b: B

    def or_else(self, default: A) -> A:
        return default

    def map(self, f):
        return self

    def __eq__(self, other):
        """
        Test if ``other`` is an :class:`Error` wrapping the same value as
        this instance

        :example:
        >>> Error('error message') == Error('error message')
        True
        >>> Error('error message') == Error('another message')
        False

        :param other: object to compare with
        :return: True if other is an :class:`Error` instance and wraps the same
        value as this instance, False otherwise
        """
        return isinstance(other, Right) and other.b == self.b

    def __bool__(self):
        return True

    def and_then(self, f):
        return self

    def __repr__(self):
        return f'Right({repr(self.b)})'


def either(f: Callable[..., A]) -> Callable[..., Either[A, B]]:
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
