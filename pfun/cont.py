from typing import Generic, Callable, TypeVar, Iterable, cast

from .util import compose
from .immutable import Immutable
from .monad import Monad, sequence_, map_m_, filter_m_
from .curry import curry

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')
D = TypeVar('D')


class Cont(Generic[A, B], Monad, Immutable):
    """
    Type that represents a function in continuation passing style.
    """
    f: Callable[[Callable[[A], B]], B]

    def and_then(self, f: 'Callable[[B], Cont[C, D]]') -> 'Cont[C, D]':
        """
        Chain together functions in continuation passing style

        :example:
        >>> value(1).and_then(lambda i: value(i + 1)).run(identity)
        2

        :param f: Function in continuation passing style to chain with
        the result of this function
        :return:
        """
        return Cont(lambda c: self.run(lambda a: f(a).run(c)))  # type: ignore

    def run(self, f: Callable[[A], B]) -> B:
        """
        Run the wrapped function in continuation passing style by passing the
        result to ``f``

        :example:
        >>> from pfun import identity
        >>> value(1).run(identity)
        1

        :param f: The function to pass the result of the wrapped function to
        :return: the result of passing the return value
        of the wrapped function to ``f``
        """
        return self.f(f)  # type: ignore

    __call__ = run

    def map(self, f: Callable[[B], C]) -> 'Cont[B, C]':
        """
        Map the  ``f`` over this continuation

        :example:
        >>> from pfun import identity
        >>> value(1).map(lambda v: v + 1).run(identity)
        2

        :param f: The function to map over this continuation
        :return: Continuation mapped with ``f``
        """
        return Cont(lambda c: self.run(compose(c, f)))  # type: ignore


@curry
def map_m(f: Callable[[A], Cont[A, B]],
          iterable: Iterable[A]) -> Cont[Iterable[A], B]:
    """
    Apply ``f`` to each element in ``iterable`` and collect the results

    :example:
    >>> from pfun import identity
    >>> map_m(value, range(3)).run(identity)
    (0, 1, 2)

    :param f: The function to map over ``iterable``
    :param iterable: The iterable to map over
    :return: ``iterable`` mapped with ``f`` inside Cont
    """
    return cast(Cont[Iterable[A], B], map_m_(value, f, iterable))


def sequence(iterable: Iterable[Cont[A, B]]) -> Cont[Iterable[A], B]:
    """
    Gather an iterable of continuation results into one iterable

    :example:
    >>> from pfun import identity
    >>> sequence([value(v) for v in range(3)]).run(identity)
    (0, 1, 2)

    :param iterable: An iterable of continuation results
    :return: Continuation results
    """
    return cast(Cont[Iterable[A], B], sequence_(value, iterable))


@curry
def filter_m(f: Callable[[A], Cont[bool, B]],
             iterable: Iterable[A]) -> Cont[Iterable[A], B]:
    """
    Filter elements by in ``iterable`` by ``f`` and combine results into
    an iterable as a continuation

    :example:
    >>> from pfun import identity
    >>> filter_m(lambda v: value(v % 2 == 0), range(3)).run(identity)
    (0, 2)

    :param f: Function to filter by
    :param iterable: Iterable to filter
    :return: Elements in ``iterable`` filtered by ``f`` as a continuation
    """
    return cast(Cont[Iterable[A], B], filter_m_(value, f, iterable))


def value(a: A) -> Cont[A, B]:
    """
    Wrap a constant value in a :class:`Cont` context

    :example:
    >>> from pfun import identity
    >>> value(1).run(identity)
    1

    :param a: Constant value to wrap
    :return: :class:`Cont` wrapping the value
    """
    return Cont(lambda cont: cont(a))


__all__ = ['value', 'filter_m', 'sequence', 'map_m', 'Cont']
