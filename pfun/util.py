from typing import TypeVar, Callable, Any, Type, Union

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')


def identity(v: A) -> A:
    """
    The identity function. Just gives back its argument

    :example:
    >>> identity('value')
    'value'

    :param v: The value to get back
    :return: v
    """
    return v


Unary = Callable[[A], B]


def compose(f: Unary[B, C], g: Unary[A, B]) -> Unary[A, C]:
    return lambda z: f(g(z))


Predicate = Callable[[A], bool]


def flip(f: Unary[A, Unary[B, C]]) -> Unary[B, Unary[A, C]]:
    def _(b):
        def _(a):
            return f(a)(b)
        return _
    return _

