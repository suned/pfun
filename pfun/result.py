from typing import Generic, TypeVar, Callable, Any
from functools import wraps
from .immutable import Immutable

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')


class Result(Generic[A, B], Immutable):
    """
    Abstract class representing a potentially failed computation.
    Should not be instantiated directly, use :class:`Ok` or :class:`Error` instead
    """
    def __init__(self):
        raise TypeError("'Result' should not be instantiated directly. Use Ok or Error instead")

    def and_then(self, f: Callable[[A], 'Result[A, B]']) -> 'Result[A, B]':
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

    def __bool__(self):
        """
        Convert this result to a boolean value

        :example:
        >>> "Ok" if Ok(1) else "Error"
        "Ok"
        >>> "Ok" if Error("an error") else "Error"
        "Error"

        :return: True if this as an :class:`Ok`, False if this is an :class:`Error`
        """
        raise NotImplementedError()

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

    def map(self, f: Callable[[A], C]) -> 'Result[C, B]':
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


class Ok(Result[A, B]):
    """
    Represents a successful computation of type A
    """

    def or_else(self, default: A) -> A:
        return self.a

    def __init__(self, a: A):
        """
        Initialize value representing a successful computation of type A
        :param a: Result of the succesful computation
        """
        self.a = a

    def map(self, f):
        return Ok(f(self.a))

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
        return isinstance(other, Ok) and self.a == other.a

    def __bool__(self) -> bool:
        return True

    def __repr__(self):
        return f'Ok({repr(self.a)})'


class Error(Result[A, B]):
    def or_else(self, default: A) -> A:
        return default

    def __init__(self, b: B):
        """
        Initialize a value representing a failed computation of type B

        :param b: The cause of the failed computation
        """
        self.b = b

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
        :return: True if other is an :class:`Error` instance and wraps the same \
        value as this instance, False otherwise
        """
        return isinstance(other, Error) and other.b == self.b

    def __bool__(self):
        return False

    def and_then(self, f):
        return self

    def __repr__(self):
        return f'Error({repr(self.b)})'


def result(f: Callable[[A], B]) -> Callable[[A], Result[B, Exception]]:
    """
    Wrap a function that may raise an exception with a :class:`Result`.
    Can also be used as a decorator. Useful for turning
    any function into a monadic function

    :example:
    >>> to_int = result(int)
    >>> to_int("1")
    Ok(1)
    >>> to_int("Whoops")
    Error(ValueError("invalid literal for int() with base 10: 'Whoops'"))

    :param f: Function to wrap
    :return: f wrapped with a :class:`Result`
    """
    @wraps(f)
    def dec(*args, **kwargs):
        try:
            return Ok(f(*args, **kwargs))
        except Exception as e:
            return Error(e)

    return dec
