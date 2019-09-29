from typing import TypeVar, Callable
from functools import wraps

from .either import Either, Left, Right

A = TypeVar('A')
B = TypeVar('B')


class Result(Either[Exception, A]):
    """
    Represents computations that may fail with an exception
    """
    pass


class Ok(Result[A], Right[Exception, A]):
    """
    Represents a succesful computation
    """
    pass


class Error(Result[A], Left[Exception, A]):
    """
    Represents a failed computation
    """
    b: Exception


def result(f: Callable[..., B]) -> Callable[..., Result[B]]:
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


__all__ = ['Result', 'Ok', 'Error', 'result']
