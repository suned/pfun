from functools import singledispatch

from typing import Union, List, Tuple, TypeVar


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
