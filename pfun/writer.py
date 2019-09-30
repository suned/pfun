from typing import Generic, Callable, TypeVar, Iterable, cast
from pfun.monoid import M, append, empty
from .immutable import Immutable
from .curry import curry
from .monad import map_m_, Monad, sequence_, filter_m_

A = TypeVar('A')
B = TypeVar('B')


class Writer(Generic[A, M], Immutable, Monad):
    """
    Represents a value
    along with a monoid value that is accumulated as
    an effect

    """
    a: A
    m: M

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
        :return: :class:`Writer` with result of
                 passing the value in this :class:`Writer`
                 to ``f``, and appending the monoid in this
                 instance with the result of ``f``
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

    def __eq__(self, other):
        if not isinstance(other, Writer):
            return False
        return other.a == self.a and other.m == self.m

    def map(self, f: 'Callable[[A], B]') -> 'Writer[B, M]':
        """
        Map the value/monoid pair in this :class:`Writer`

        :example:
        >>> Writer('value', []).map(lambda v, m: ('new value', ['new monoid']))
        Writer('new value', ['new monoid'])

        :param f: the function to map the value and
                  monoid in this :class:`Writer`
        :return: :class:`Writer` with value and monoid mapped by ``f``
        """
        return Writer(f(self.a), self.m)

    def __repr__(self):
        a_repr = repr(self.a)
        m_repr = repr(self.m) if self.m is not ... else "..."
        return f'Writer({a_repr}, {m_repr})'


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


def tell(m: M) -> Writer[None, M]:
    """
    Create a Writer with a monoid ``m`` and unit value

    :example:
    >>> tell(
    ...     ['monoid value']
    ... ).and_then(
    ...     lambda _: tell(['another monoid value'])
    ... )
    Writer(None, ['monoid value', 'another monoid value'])

    :param m: the monoid value
    :return: Writer with unit value and monoid value ``m``
    """
    return Writer(None, m)


def sequence(iterable: Iterable[Writer[A, M]]) -> Writer[Iterable[A], M]:
    """
    Evaluate each :class:`Writer` in `iterable` from left to right
    and collect the results

    :example:
    >>> sequence([value(v) for v in range(3)])
    Writer((0, 1, 2), ...)

    :param iterable: The iterable to collect results from
    :returns: ``Writer`` of collected results
    """
    return cast(Writer[Iterable[A], M], sequence_(value, iterable))


@curry
def filter_m(f: Callable[[A], Writer[bool, M]],
             iterable: Iterable[A]) -> Writer[Iterable[A], M]:
    """
    Map each element in ``iterable`` by applying ``f``,
    filter the results by the value returned by ``f``
    and combine from left to right.

    :example:
    >>> filter_m(lambda v: value(v % 2 == 0), range(3))
    Writer((0, 2), ...)

    :param f: Function to map ``iterable`` by
    :param iterable: Iterable to map by ``f``
    :return:
    """
    return cast(Writer[Iterable[A], M], filter_m_(value, f, iterable))


@curry
def map_m(f: Callable[[A], Writer[B, M]],
          iterable: Iterable[A]) -> Writer[Iterable[B], M]:
    """
    Map each in element in ``iterable`` to
    an :class:`Writer` by applying ``f``,
    combine the elements by ``and_then``
    from left to right and collect the results

    :example:
    >>> map_m(value, range(3))
    Writer((0, 1, 2), ...)

    :param f: Function to map over ``iterable``
    :param iterable: Iterable to map ``f`` over
    :return: ``f`` mapped over ``iterable`` and combined from left to right.
    """
    return cast(Writer[Iterable[B], M], map_m_(value, f, iterable))


__all__ = ['Writer', 'value', 'tell', 'sequence', 'map_m', 'filter_m']
