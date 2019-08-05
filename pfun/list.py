from typing import List as List_, TypeVar, Callable, Iterable, Tuple, Optional
from functools import reduce

from pfun.monoid import Monoid

A = TypeVar('A')
B = TypeVar('B')


class List(List_[A], Monoid):
    def empty(self) -> 'List[A]':
        return List()

    def reduce(self, f: Callable[[B, A], B], initializer: Optional[B] = None) -> 'List[B]':
        """
        Aggregate elements by ``f``

        :example:
        >>> List(range(3)).reduce(sum)
        3

        :param f: Function to perform aggregation
        :param initializer: Starting value for aggregation
        :return: Aggregated result
        """
        return reduce(f, self, initializer)  # type: ignore

    def __setitem__(self, key, value):
        raise TypeError("'List' object does not support item assignment")

    def append(self, a: 'List[A]') -> 'List[A]':  # type: ignore
        """
        Add element to end of list

        :example:
        >>> List(range(3)).append(3)
        [1, 2, 3]

        :param a: Element to append
        :return: New :class:`List` with ``a`` appended
        """
        return self + a

    def extend(self, iterable: Iterable[A]) -> 'List[A]':  # type: ignore
        """
        Add all elements from ``iterable`` to end of list

        :example:
        >>> List(range(3)).extend(range(3))
        [0, 1, 2, 0, 1, 2]

        :param iterable: Iterable to extend by
        :return: New :class:`List` with extended by ``iterable``
        """
        return self + list(iterable)

    def __add__(self, other: List_[A]) -> 'List[A]':
        """
        Concatenate with other ``list`` or :class:`List`

        :example:
        >>> List(range(2)) + List(range(2))
        [0, 1, 0, 1]

        :param other: list to concatenate with
        :return: new :class:`List` concatenated with ``other``
        """
        return List(super().__add__(other))

    def __radd__(self, other):
        """
        Concatenate with other ``list`` or :class:`List`

        :example:
        >>> List(range(2)) + List(range(2))
        [0, 1, 0, 1]

        :param other: list to concatenate with
        :return: new :class:`List` concatenated with ``other``
        """
        return List(other.__add__(self))

    def map(self, f: Callable[[A], B]) -> 'List[B]':
        """
        Apply ``f`` to each element in the list

        :example:
        >>> List(range(2)).map(str)
        ['0', '1']

        :param f: Function to apply
        :return: new :class:`List` mapped by ``f``
        """
        return List(map(f, self))

    def filter(self, f: Callable[[A], bool]) -> 'List[A]':
        """
        Filter elements by the predicate ``f``

        :example:
        >>> List(range(4)).filter(lambda e: e % 2 == 0)
        [0, 2]

        :param f: Function to filter by
        :return: new :class:`List` filtered by ``f``
        """
        return List(filter(f, self))

    def and_then(self, f: 'Callable[[A], List[B]]') -> 'List[B]':
        """
        Chain together functions that produce more than one result

        :example:
        >>> List(range(4)).and_then(lambda v: List(range(v)))
        [0, 0, 1, 0, 1, 2]

        :param f: Function to apply to elements of this :class:`List`
        :return: Concatenated results from applying ``f`` to all elements
        """
        return self.reduce(lambda l, v: l + f(v), List())  # type: ignore

    def zip(self, other: Iterable[B]) -> Iterable[Tuple[A, B]]:
        """
        Zip together with another iterable

        :example:
        >>> List(List(range(2)).zip(range(2)))
        [(0, 0), (1, 1)]

        :param other: Iterable to zip with
        :return: Zip with ``other``
        """
        return zip(self, other)

    def reverse(self):
        return List(reversed(self))

    def __delitem__(self, key):
        raise TypeError("'List' object does not support item deletion")
