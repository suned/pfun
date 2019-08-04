from typing import Union, List, Tuple, TypeVar, Generic, Callable, Type

from functools import singledispatch

from .unit import Unit
from .immutable import Immutable


class Monoid:
    """
    Abstract class for implementing custom Monoids that can be used
    with the :class:`Writer` monad

    """
    def append(self, other: 'Monoid') -> 'Monoid':
        """
        Append function for the Monoid type

        :param other: Other Monoid type to append to this one
        :return: Result of appending other to this Monoid
        """
        raise NotImplementedError()

    def empty(self) -> 'Monoid':
        """
        empty value for the Monoid type

        :return: empty value
        """
        raise NotImplementedError()


M_ = Union[int, List, Tuple, str, None, Monoid]
M = TypeVar('M', bound=M_)

A = TypeVar('A')
B = TypeVar('B')


@singledispatch
def append(a: M, b: M) -> M:
    raise NotImplementedError()


@append.register
def append_monoid(a: Monoid, b: Monoid) -> Monoid:
    return a.append(b)


@append.register
def append_int(a: int, b: int) -> int:
    return a + b


@append.register
def append_list(a: list, b: list) -> list:
    return a + b


@append.register
def append_str(a: str, b: str) -> str:
    return a + b


@append.register
def append_none(a: None, b: None) -> None:
    return None


@append.register
def append_tuple(a: tuple, b: tuple) -> tuple:
    return a + b


@singledispatch
def empty(t):
    raise NotImplementedError()


@empty.register
def empty_int(t: int) -> int:
    return 0


@empty.register
def empty_list(t: list) -> list:
    return []


@empty.register
def empty_tuple(t: tuple) -> tuple:
    return ()


@empty.register
def empty_monoid(t: Monoid) -> Monoid:
    return t.empty()


@empty.register
def empty_str(t: str) -> str:
    return ''


@empty.register
def empty_none(t: None) -> None:
    return None


class Writer(Generic[A, M], Immutable):
    """
    Class that represents a value along with a monoid value that is accumulated as
    a side effect

    """
    def __init__(self, a: A, m: M):
        """
        Initialize a value and monoid pair

        :param a: value
        :param m: monoid value
        """
        self.a = a
        self.m = m

    def and_then(self, f: 'Callable[[A], Writer[B, M]]') -> 'Writer[B, M]':
        """
        Pass the value in this value/monoid pair to ``f``,
        and then combine the resulting monoid with the monoid in this pair

        :example:
        >>> Writer(1, ['first element']).and_then(
        ...     lambda i: Writer(i + 1, ['second element'])
        ... )
        Writer(2, ['first element', 'second element'])

        :param f: Function to pass the value to
        :return: :class:`Writer` with result of passing the value in this :class:`Writer` \
        to ``f``, and appending the monoid in this instance with the result of ``f``
        """

        # this is kind of a hack:
        # I'm using ... as a special symbol that represents a monoid value
        # the type of which is yet to be determined.
        w = f(self.a)
        if w.m is ... and self.m is ...:
            m = ...
        elif w.m is ...:
            m = append(self.m, empty(self.m))  # type: ignore
        elif self.m is ...:
            m = append(empty(w.m), w.m)  # type: ignore
        else:
            m = append(self.m, w.m)  # type: ignore
        return Writer(w.a, m)  # type: ignore

    def map(self, f: 'Callable[[A, M], Tuple[B, M]]') -> 'Writer[B, M]':
        """
        Map the value/monoid pair in this :class:`Writer`

        :example:
        >>> Writer('value', []).map(lambda v, m: ('new value', ['new monoid']))
        Writer('new value', ['new monoid'])

        :param f: the function to map the value and monoid in this :class:`Writer`
        :return: :class:`Writer` with value and monoid mapped by ``f``
        """
        return Writer(*f(self.a, self.m))

    def __repr__(self):
        return f'Writer({repr(self.a)}, {repr(self.m) if self.m is not ... else "..."})'


def value(a: A, m: M = ...) -> Writer[A, M]:  # type: ignore
    """
    Put a value in a :class:`Writer` context

    :example:
    >>> value(1)
    Writer(1, ...)
    >>> value(1, ['some monoid'])
    Writer(1, ['some monoid'])

    :param a: The value to put in the :class:`Writer` context
    :param m: Optional monoid to associate with ``a``
    :return: :class:`Writer` with ``a`` and optionally ``m``
    """
    return Writer(a, m)


def tell(m: M) -> Writer[Unit, M]:
    """
    Create a Writer with a monoid ``m`` and unit value

    :example:
    >>> tell(
    ...     ['monoid value']
    ... ).and_then(
    ...     lambda _: tell(['another monoid value'])
    ... )
    Writer((), ['monoid value', 'another monoid value'])

    :param m: the monoid value
    :return: Writer with unit value and monoid value ``m``
    """
    return Writer((), m)
