from typing import TypeVar, Generic, Callable, Iterable, cast

from pfun.immutable import Immutable
from abc import ABC, abstractmethod

from .functor import Functor
from .monad import Monad, sequence_, map_m_, filter_m_
from .curry import curry
from .state import State, get

A = TypeVar('A')
B = TypeVar('B')

C = TypeVar('C')
D = TypeVar('D')


class FreeInterpreter(Generic[C, D], ABC):
    """
    An interpreter to map a ``Free`` structure into a `D` from a `C`.
    """
    def interpret(self, root: 'FreeInterpreterElement[C, D]') -> State[C, D]:
        """
        Run the interpreter on the root element recursively

        :param root: The root interpreter element
        :return: The result of interpreting ``root``
        """
        return root.accept(self)

    def interpret_more(self, more) -> State[C, D]:
        return more.k.accept(self)

    def interpret_done(self, done) -> State[C, D]:
        return get()  # type: ignore


class FreeInterpreterElement(Functor, Generic[C, D], ABC):
    """
    An element in a ``Free`` structure that can be interepreted
    """
    @abstractmethod
    def accept(self, interpreter: FreeInterpreter[C, D]) -> State[C, D]:
        """
        Interpret this element

        :param interpreter: The interpreter to apply to this element
        :return: The result of using ``interpreter` to interpret this element
        """
        pass


F = TypeVar('F', bound=Functor)


class Free(
    Generic[F, A, C, D], FreeInterpreterElement[C, D], Monad, Immutable
):
    """
    The "Free" monad
    """
    @abstractmethod
    def and_then(
        self, f: 'Callable[[A], Free[F, B, C, D]]'
    ) -> 'Free[F, B, C, D]':
        pass

    def map(self, f: Callable[[A], B]) -> 'Free[F, B, C, D]':
        return self.and_then(lambda v: Done(f(v)))


class Done(Free[F, A, C, D]):
    """
    Pure ``Free`` value
    """
    a: A

    def and_then(self, f: Callable[[A], Free[F, B, C, D]]) -> Free[F, B, C, D]:
        """
        Apply ``f`` to the value wrapped in this ``Done``

        :param f: The function to apply to the value wrapped in this ``Done``
        :return: The result of applying ``f`` to the value in this ``Done``
        """
        return f(self.a)

    def accept(self, interpreter: FreeInterpreter[C, D]) -> State[C, D]:
        """
        Run an interpreter on this ``Done``

        :param interpreter: The interpreter to run on on this ``Done`` instance
        :return: The result of interpreting this ``Done`` instance
        """
        return interpreter.interpret_done(self)


class More(Free[F, A, C, D]):
    """
    A ``Free`` value wrapping a `Functor` value
    """
    k: Functor

    def and_then(self, f: Callable[[A], Free[F, B, C, D]]) -> Free[F, B, C, D]:
        """
        Apply ``f`` to the value wrapped in the functor of this ``More``

        :param f: The function to apply to the functor value
        :return: The result of applying ``f`` to the functor of this ``More``
        """
        return More(self.k.map(lambda v: v.and_then(f)))

    def accept(self, interpreter: FreeInterpreter[C, D]) -> State[C, D]:
        """
        Run an interpreter on this ``More``

        :param interepreter: The intepreter to run on this ``More`` instance
        :return: The result of running ``interpreter`` on this ``More``
        """
        return interpreter.interpret_more(self)


@curry
def map_m(f: Callable[[A], Free[F, B, C, D]],
          iterable: Iterable[A]) -> Free[F, Iterable[B], C, D]:
    """
    Map each in element in ``iterable`` to
    a :class:`Free` by applying ``f``,
    combine the elements by ``and_then``
    from left to right and collect the results

    :param f: Function to map over ``iterable``
    :param iterable: Iterable to map ``f`` over
    :return: ``f`` mapped over ``iterable`` and combined from left to right.
    """
    return cast(Free[F, Iterable[B], C, D], map_m_(Done, f, iterable))


def sequence(iterable: Iterable[Free[F, A, C, D]]
             ) -> Free[F, Iterable[A], C, D]:
    """
    Evaluate each ``Free`` in `iterable` from left to right
    and collect the results

    :param iterable: The iterable to collect results from
    :returns: ``Free`` of collected results
    """
    return cast(Free[F, Iterable[A], C, D], sequence_(Done, iterable))


@curry
def filter_m(f: Callable[[A], Free[F, bool, C, D]],
             iterable: Iterable[A]) -> Free[F, Iterable[A], C, D]:
    """
    Map each element in ``iterable`` by applying ``f``,
    filter the results by the value returned by ``f``
    and combine from left to right.

    :param f: Function to map ``iterable`` by
    :param iterable: Iterable to map by ``f``
    :return:
    """
    return cast(Free[F, Iterable[A], C, D], filter_m_(Done, f, iterable))


__all__ = [
    'FreeInterpreter',
    'FreeInterpreterElement',
    'Free',
    'Done',
    'More',
    'map_m',
    'sequence',
    'filter_m'
]
