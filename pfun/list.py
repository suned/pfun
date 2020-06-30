from functools import reduce
from typing import (Callable, Generator, Generic, Iterable, Optional, Tuple,
                    TypeVar, cast)

from .curry import curry
from .immutable import Immutable
from .monad import Monad, filter_m_, map_m_, sequence_
from .monoid import Monoid
from .with_effect import with_effect_eager

A = TypeVar('A')
B = TypeVar('B')


class List(Monoid, Monad, Generic[A], Iterable[A], Immutable, init=False):
    _iterable: Tuple[A]

    def __init__(self, iterable: Iterable[A] = ()):
        object.__setattr__(self, '_iterable', tuple(iterable))

    def __repr__(self):
        return f"List({repr(self._iterable)})"

    def empty(self) -> 'List[A]':
        return List()

    def reduce(
        self, f: Callable[[B, A], B], initializer: Optional[B] = None
    ) -> B:
        """
        Aggregate elements by ``f``

        :example:
        >>> List(range(3)).reduce(sum)
        3

        :param f: Function to perform aggregation
        :param initializer: Starting value for aggregation
        :return: Aggregated result
        """
        return reduce(f, self._iterable, initializer)  # type: ignore

    def append(self, a: A) -> 'List[A]':
        """
        Add element to end of list

        :example:
        >>> List(range(3)).append(3)
        [1, 2, 3]

        :param a: Element to append
        :return: New :class:`List` with ``a`` appended
        """
        return List(self._iterable + (a,))

    def extend(self, iterable: Iterable[A]) -> 'List[A]':
        """
        Add all elements from ``iterable`` to end of list

        :example:
        >>> List(range(3)).extend(range(3))
        [0, 1, 2, 0, 1, 2]

        :param iterable: Iterable to extend by
        :return: New :class:`List` with extended by ``iterable``
        """
        return self + list(iterable)

    def __add__(self, other: Iterable[A]) -> 'List[A]':
        """
        Concatenate with other ``list`` or :class:`List`

        :example:
        >>> List(range(2)) + List(range(2))
        [0, 1, 0, 1]

        :param other: list to concatenate with
        :return: new :class:`List` concatenated with ``other``
        """
        return List(self._iterable + tuple(other))

    def __radd__(self, other: Iterable[A]) -> 'List[A]':
        """
        Concatenate with other ``list`` or :class:`List`

        :example:
        >>> List(range(2)) + List(range(2))
        [0, 1, 0, 1]

        :param other: list to concatenate with
        :return: new :class:`List` concatenated with ``other``
        """
        return List(tuple(other) + self._iterable)

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
        return List(filter(f, self._iterable))

    def and_then(self, f: 'Callable[[A], List[B]]') -> 'List[B]':
        """
        Chain together functions that produce more than one result

        :example:
        >>> List(range(4)).and_then(lambda v: List(range(v)))
        [0, 0, 1, 0, 1, 2]

        :param f: Function to apply to elements of this :class:`List`
        :return: Concatenated results from applying ``f`` to all elements
        """
        return self.reduce(lambda l, v: l + f(v), List())

    def zip(self, other: Iterable[B]) -> Iterable[Tuple[A, B]]:
        """
        Zip together with another iterable

        :example:
        >>> List(List(range(2)).zip(range(2)))
        [(0, 0), (1, 1)]

        :param other: Iterable to zip with
        :return: Zip with ``other``
        """
        return zip(self._iterable, other)

    def reverse(self) -> 'List[A]':
        return List(reversed(self._iterable))

    def __len__(self):
        return len(self._iterable)

    def __iter__(self):
        return iter(self._iterable)


def value(a: A) -> List[A]:
    return List([a])


@curry
def map_m(f: Callable[[A], List[B]],
          iterable: Iterable[A]) -> List[Iterable[B]]:
    """
    Map each in element in ``iterable`` to
    an :class:`List` by applying ``f``,
    combine the elements by ``and_then``
    from left to right and collect the results

    :example:
    >>> map_m(Just, range(3))
    Just((0, 1, 2))

    :param f: Function to map over ``iterable``
    :param iterable: Iterable to map ``f`` over
    :return: ``f`` mapped over ``iterable`` and combined from left to right.
    """
    return cast(List[Iterable[B]], map_m_(value, f, iterable))


def sequence(iterable: Iterable[List[A]]) -> List[Iterable[A]]:
    """
    Evaluate each :class:`List` in `iterable` from left to right
    and collect the results

    :example:
    >>> sequence([Just(v) for v in range(3)])
    Just((0, 1, 2))

    :param iterable: The iterable to collect results from
    :returns: ``List`` of collected results
    """
    return cast(List[Iterable[A]], sequence_(value, iterable))


@curry
def filter_m(f: Callable[[A], List[bool]],
             iterable: Iterable[A]) -> List[Iterable[A]]:
    """
    Map each element in ``iterable`` by applying ``f``,
    filter the results by the value returned by ``f``
    and combine from left to right.

    :example:
    >>> filter_m(lambda v: Just(v % 2 == 0), range(3))
    Just((0, 2))

    :param f: Function to map ``iterable`` by
    :param iterable: Iterable to map by ``f``
    :return: `iterable` mapped and filtered by `f`
    """
    return cast(List[Iterable[A]], filter_m_(value, f, iterable))


Lists = Generator[List[A], A, B]


def with_effect(f: Callable[..., Lists[A, B]]) -> Callable[..., List[B]]:
    """
    Decorator for functions that
    return a generator of lists and a final result.
    Iteraters over the yielded lists and sends back the
    unwrapped values using "and_then"

    :example:
    >>> @with_effect
    ... def f() -> Lists[int, int]:
    ...     a = yield List([2])
    ...     b = yield List([2])
    ...     return a + b
    >>> f()
    List((4,))

    :param f: generator function to decorate
    :return: `f` decorated such that generated :class:`List` \
        will be chained together with `and_then`
    """
    return with_effect_eager(value, f)  # type: ignore


__all__ = [
    'List', 'value', 'map_m', 'sequence', 'filter_m', 'Lists', 'with_effect'
]
