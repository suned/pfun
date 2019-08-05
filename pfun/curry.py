from typing import TypeVar, Callable
import functools
import inspect

from pfun import compose
from .immutable import Immutable

A1 = TypeVar('A1')
A2 = TypeVar('A2')
A3 = TypeVar('A3')
A4 = TypeVar('A4')
A5 = TypeVar('A5')
A6 = TypeVar('A6')
A7 = TypeVar('A7')
A8 = TypeVar('A8')
A9 = TypeVar('A9')
A10 = TypeVar('A10')
A11 = TypeVar('A11')
A12 = TypeVar('A12')
R = TypeVar('R')


def curry2(
        f: Callable[[A1, A2], R]
) -> Callable[[A1], Callable[[A2], R]]:
    """
    Typed version of :py:func:`curry`

    :param f: Function to curry
    :return: Curried version of ``f``
    """
    return curry(f)


def curry3(
        f: Callable[[A1, A2, A3], R]
) -> Callable[[A1], Callable[[A2], Callable[[A3], R]]]:
    """
    Typed version of :py:func:`curry`

    :param f: Function to curry
    :return: Curried version of ``f``
    """
    return curry(f)


def curry4(
        f: Callable[[A1, A2, A3, A4], R]
) -> Callable[[A1], Callable[[A2], Callable[[A3], Callable[[A4], R]]]]:
    """
    Typed version of :py:func:`curry`

    :param f: Function to curry
    :return: Curried version of ``f``
    """
    return curry(f)


def curry5(
    f: Callable[[A1, A2, A3, A4, A5], R]
) -> Callable[
    [A1],
    Callable[
        [A2],
        Callable[
            [A3],
            Callable[
                [A4],
                Callable[[A5], R]
            ]
        ]
    ]
]:
    """
    Typed version of :py:func:`curry`

    :param f: Function to curry
    :return: Curried version of ``f``
    """
    return curry(f)


def curry6(
    f: Callable[[A1, A2, A3, A4, A5, A6], R]
) -> Callable[
    [A1],
    Callable[
        [A2],
        Callable[
            [A3],
            Callable[
                [A4],
                Callable[
                    [A5],
                    Callable[[A6], R]
                ]
            ]
        ]
    ]
]:
    """
    Typed version of :py:func:`curry`

    :param f: Function to curry
    :return: Curried version of ``f``
    """
    return curry(f)


def curry7(
    f: Callable[[A1, A2, A3, A4, A5, A6, A7], R]
) -> Callable[
    [A1],
    Callable[
        [A2],
        Callable[
            [A3],
            Callable[
                [A4],
                Callable[
                    [A5],
                    Callable[
                        [A6],
                        Callable[[A7], R]
                    ]
                ]
            ]
        ]
    ]
]:
    """
    Typed version of :py:func:`curry`

    :param f: Function to curry
    :return: Curried version of ``f``
    """
    return curry(f)


def curry8(
    f: Callable[[A1, A2, A3, A4, A5, A6, A7, A8], R]
) -> Callable[
    [A1],
    Callable[
        [A2],
        Callable[
            [A3],
            Callable[
                [A4],
                Callable[
                    [A5],
                    Callable[
                        [A6],
                        Callable[
                            [A7],
                            Callable[
                                [A8],
                                R
                            ]
                        ]
                    ]
                ]
            ]
        ]
    ]
]:
    """
    Typed version of :py:func:`curry`

    :param f: Function to curry
    :return: Curried version of ``f``
    """
    return curry(f)


def curry9(
    f: Callable[[A1, A2, A3, A4, A5, A6, A7, A8, A9], R]
) -> Callable[
    [A1],
    Callable[
        [A2],
        Callable[
            [A3],
            Callable[
                [A4],
                Callable[
                    [A5],
                    Callable[
                        [A6],
                        Callable[
                            [A7],
                            Callable[
                                [A8],
                                Callable[[A9], R]
                            ]
                        ]
                    ]
                ]
            ]
        ]
    ]
]:
    """
    Typed version of :py:func:`curry`

    :param f: Function to curry
    :return: Curried version of ``f``
    """
    return curry(f)


def curry10(
    f: Callable[[A1, A2, A3, A4, A5, A6, A7, A8, A9, A10], R]
) -> Callable[
    [A1],
    Callable[
        [A2],
        Callable[
            [A3],
            Callable[
                [A4],
                Callable[
                    [A5],
                    Callable[
                        [A6],
                        Callable[
                            [A7],
                            Callable[
                                [A8],
                                Callable[
                                    [A9],
                                    Callable[[A10], R]
                                ]
                            ]
                        ]
                    ]
                ]
            ]
        ]
    ]
]:
    """
    Typed version of :py:func:`curry`

    :param f: Function to curry
    :return: Curried version of ``f``
    """
    return curry(f)


def curry11(
    f: Callable[[A1, A2, A3, A4, A5, A6, A7, A8, A9, A10, A11], R]
) -> Callable[
    [A1],
    Callable[
        [A2],
        Callable[
            [A3],
            Callable[
                [A4],
                Callable[
                    [A5],
                    Callable[
                        [A6],
                        Callable[
                            [A7],
                            Callable[
                                [A8],
                                Callable[
                                    [A9],
                                    Callable[
                                        [A10],
                                        Callable[[A11], R]
                                    ]
                                ]
                            ]
                        ]
                    ]
                ]
            ]
        ]
    ]
]:
    """
    Typed version of :py:func:`curry`

    :param f: Function to curry
    :return: Curried version of ``f``
    """
    return curry(f)


def curry12(
    f: Callable[[A1, A2, A3, A4, A5, A6, A7, A8, A9, A10, A11, A12], R]
) -> Callable[
    [A1],
    Callable[
        [A2],
        Callable[
            [A3],
            Callable[
                [A4],
                Callable[
                    [A5],
                    Callable[
                        [A6],
                        Callable[
                            [A7],
                            Callable[
                                [A8],
                                Callable[
                                    [A9],
                                    Callable[
                                        [A10],
                                        Callable[
                                            [A11],
                                            Callable[[A12], R]
                                        ]
                                    ]
                                ]
                            ]
                        ]
                    ]
                ]
            ]
        ]
    ]
]:
    """
    Typed version of :py:func:`curry`

    :param f: Function to curry
    :return: Curried version of ``f``
    """
    return curry(f)


class Curry(Immutable):
    def __init__(self, f):
        self.f = f

    def __repr__(self):
        return repr(self.f)

    def __call__(self, *args, **kwargs):
        signature = inspect.signature(self.f)
        bound = signature.bind_partial(*args, **kwargs)
        bound.apply_defaults()
        arg_names = {a for a in bound.arguments.keys()}
        parameters = {p for p in signature.parameters.keys()}
        if parameters - arg_names == set():
            return self.f(*args, **kwargs)
        partial = functools.partial(self.f, *args, **kwargs)
        return Curry(partial)


def curry(f):
    """
    Get a version of ``f`` that can be partially applied

    :example:
    >>> f = lambda a, b: a + b
    >>> f_curried = curry(f)
    >>> f_curried(1)
    functools.partial(<function <lambda> at 0x1051f0950>, a=1)
    >>> f_curried(1)(1)
    2

    :param f: The function to curry
    :return: Curried version of ``f``
    """

    @functools.wraps(f)
    def decorator(*args, **kwargs):
        return Curry(f)(*args, **kwargs)

    return decorator
