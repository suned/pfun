from functools import reduce
from typing import Callable, Iterable, Optional, Tuple, TypeVar, cast

from .functions import curry
from .monad import Monad, filter_m_, map_m_, sequence_

A = TypeVar('A')
B = TypeVar('B')


class List(Monad, Tuple[A, ...]):

    def __repr__(self):
        return f"List({super().__repr__()})"

    def empty(self) -> 'List[A]':
        return List()

    def reduce(
        self, f: Callable[[B, A], B], initializer: Optional[B] = None
    ) -> B:
        """
        Aggregate elements by ``f``

        Example:
            >>> List(range(3)).reduce(lambda a, b: a + b)
            3

        Args:
            f: Function to perform aggregation
            initializer: Starting value for aggregation
        Return:
            Aggregated result
        """
        return reduce(f, self, initializer)  # type: ignore

    def append(self, a: A) -> 'List[A]':
        """
        Add element to end of list

        Example:
            >>> List(range(3)).append(3)
            [1, 2, 3]

        Args:
            a: Element to append
        Return:
            New `List` with ``a`` appended
        """
        return List(self + (a,))

    def extend(self, iterable: Iterable[A]) -> 'List[A]':
        """
        Add all elements from ``iterable`` to end of list

        Example:
            >>> List(range(3)).extend(range(3))
            [0, 1, 2, 0, 1, 2]

        Args:
            iterable: Iterable to extend by
        Return:
            New `List` with extended by ``iterable``
        """
        return self + tuple(iterable)

    def __add__(self, other: Iterable[A]) -> 'List[A]':
        """
        Concatenate with other ``Iterable`` or `List`

        Example:
            >>> List(range(2)) + range(2, 4)
            List((0, 1, 2, 3))

        Args:
            other: Iterable to concatenate with
        Return:
            new `List` concatenated with ``other``
        """
        return List(tuple(self) + tuple(other))

    def __radd__(self, other: Iterable[A]) -> 'List[A]':
        """
        Concatenate with other ``Iterable`` or `List`

        Example:
            >>> range(2) + List(range(2, 4))
            List((0, 1, 2, 3))

        Args:
            other: Iterable to concatenate with
        Return:
            new `List` concatenated with ``other``
        """
        return List(tuple(other) + tuple(self))

    def map(self, f: Callable[[A], B]) -> 'List[B]':
        """
        Apply ``f`` to each element in the list

        Example:
            >>> List(range(2)).map(str)
            ['0', '1']

        Args:
            f: Function to apply
        Return:
            new `List` mapped by ``f``
        """
        return List(map(f, self))

    def filter(self, f: Callable[[A], bool]) -> 'List[A]':
        """
        Filter elements by the predicate ``f``

        Example:
            >>> List(range(4)).filter(lambda e: e % 2 == 0)
            [0, 2]

        Args:
            f: Function to filter by
        Return:
            new `List` filtered by ``f``
        """
        return List(filter(f, self))

    def and_then(self, f: 'Callable[[A], List[B]]') -> 'List[B]':
        """
        Chain together functions that produce more than one result

        Example:
            >>> List(range(4)).and_then(lambda v: List(range(v)))
            [0, 0, 1, 0, 1, 2]

        Args:
            f: Function to apply to elements of this `List`
        Return:
            Concatenated results from applying ``f`` to all elements
        """
        return self.reduce(lambda l, v: l + f(v), List())

    def zip(self, other: Iterable[B]) -> Iterable[Tuple[A, B]]:
        """
        Zip together with another iterable

        Example:
            >>> List(List(range(2)).zip(range(2)))
            [(0, 0), (1, 1)]

        Args:
            other: Iterable to zip with
        Return:
            Zip with ``other``
        """
        return zip(self, other)

    def reverse(self) -> 'List[A]':
        return List(reversed(self))


def value(a: A) -> List[A]:
    return List([a])


@curry
def map_m(f: Callable[[A], List[B]],
          iterable: Iterable[A]) -> List[Iterable[B]]:
    """
    Map each in element in ``iterable`` to
    an `List` by applying ``f``,
    combine the elements by ``and_then``
    from left to right and collect the results

    Example:
        >>> map_m(lambda v: List([v]), range(3))
        List(((0, 1, 2),))

    Args:
        f: Function to map over ``iterable``
        iterable: Iterable to map ``f`` over
    Return:
        ``f`` mapped over ``iterable`` and combined from left to right.
    """
    return cast(List[Iterable[B]], map_m_(value, f, iterable))


def sequence(iterable: Iterable[List[A]]) -> List[Iterable[A]]:
    """
    Evaluate each `List` in `iterable` from left to right
    and collect the results

    Example:
        >>> sequence([List([v]) for v in range(3)])
        List(((0, 1, 2),))

    Args:
        iterable: The iterable to collect results from
    Return:
        ``List`` of collected results
    """
    return cast(List[Iterable[A]], sequence_(value, iterable))


@curry
def filter_m(f: Callable[[A], List[bool]],
             iterable: Iterable[A]) -> List[Iterable[A]]:
    """
    Map each element in ``iterable`` by applying ``f``,
    filter the results by the value returned by ``f``
    and combine from left to right.

    Example:
        >>> filter_m(lambda v: List([v % 2 == 0]), range(3))
        List(((0, 2),))
    Args:
        f: Function to map ``iterable`` by
        iterable: Iterable to map by ``f``
    Return:
        `iterable` mapped and filtered by `f`
    """
    return cast(List[Iterable[A]], filter_m_(value, f, iterable))


__all__ = [
    'List', 'value', 'map_m', 'sequence', 'filter_m'
]
