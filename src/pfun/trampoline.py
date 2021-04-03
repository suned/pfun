from abc import ABC, abstractmethod
from typing import Callable, Generic, Iterable, TypeVar, cast

from .functions import curry
from .immutable import Immutable
from .monad import Monad, filter_m_, map_m_, sequence_

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')


class Trampoline(Immutable, Generic[A], Monad, ABC):
    """
    Base class for Trampolines. Useful for writing stack safe-safe
    recursive functions.
    """
    @abstractmethod
    def _resume(self) -> 'Trampoline[A]':
        pass

    @abstractmethod
    def _handle_cont(
        self, cont: Callable[[A], 'Trampoline[B]']
    ) -> 'Trampoline[B]':
        pass

    @property
    def _is_done(self) -> bool:
        return isinstance(self, Done)

    def and_then(self, f: Callable[[A], 'Trampoline[B]']) -> 'Trampoline[B]':
        """
        Apply ``f`` to the value wrapped by this trampoline.

        Args:
            f: function to apply the value in this trampoline
        Return:
            Result of applying ``f`` to the value wrapped by \
            this trampoline
        """
        return AndThen(self, f)

    def map(self, f: Callable[[A], B]) -> 'Trampoline[B]':
        """
        Map ``f`` over the value wrapped by this trampoline.

        Args:
            f: function to wrap over this trampoline
        Return:
            new trampoline wrapping the result of ``f``
        """
        return self.and_then(lambda a: Done(f(a)))

    def run(self) -> A:
        """
        Interpret a structure of trampolines to produce a result

        Return:
            result of intepreting this structure of \
            trampolines
        """
        trampoline = self
        while not trampoline._is_done:
            trampoline = trampoline._resume()

        return cast(Done[A], trampoline).a


class Done(Trampoline[A]):
    """
    Represents the result of a recursive computation.
    """
    a: A

    def _resume(self) -> Trampoline[A]:
        return self

    def _handle_cont(self,
                     cont: Callable[[A], Trampoline[B]]) -> Trampoline[B]:
        return cont(self.a)


class Call(Trampoline[A]):
    """
    Represents a recursive call.
    """
    thunk: Callable[[], Trampoline[A]]

    def _handle_cont(self,
                     cont: Callable[[A], Trampoline[B]]) -> Trampoline[B]:
        return self.thunk().and_then(cont)  # type: ignore

    def _resume(self) -> Trampoline[A]:
        return self.thunk()  # type: ignore


class AndThen(Generic[A, B], Trampoline[B]):
    """
    Represents monadic bind for trampolines as a class to avoid
    deep recursive calls to ``Trampoline.run`` during interpretation.
    """
    sub: Trampoline[A]
    cont: Callable[[A], Trampoline[B]]

    def _handle_cont(self,
                     cont: Callable[[B], Trampoline[C]]) -> Trampoline[C]:
        return self.sub.and_then(self.cont).and_then(cont)  # type: ignore

    def _resume(self) -> Trampoline[B]:
        return self.sub._handle_cont(self.cont)  # type: ignore

    def and_then(  # type: ignore
        self, f: Callable[[A], Trampoline[B]]
    ) -> Trampoline[B]:
        return AndThen(
            self.sub,
            lambda x: Call(lambda: self.cont(x).and_then(f))  # type: ignore
        )


@curry
def for_each(f: Callable[[A], Trampoline[B]], iterable: Iterable[A]
             ) -> Trampoline[Iterable[B]]:
    """
    Map each in element in ``iterable`` to
    an `Trampoline` by applying ``f``,
    combine the elements by ``and_then``
    from left to right and collect the results

    Example:
        >>> map_m(Done, range(3)).run()
        (0, 1, 2)

    Args:
        f: Function to map over ``iterable``
        iterable: Iterable to map ``f`` over
    Return:
        ``f`` mapped over ``iterable`` and combined from left to right.
    """
    return cast(Trampoline[Iterable[B]], map_m_(Done, f, iterable))


def sequence(iterable: Iterable[Trampoline[A]]) -> Trampoline[Iterable[A]]:
    """
    Evaluate each `Trampoline` in `iterable` from left to right
    and collect the results

    Example:
        >>> sequence([Done(v) for v in range(3)]).run()
        (0, 1, 2)

    Args:
        iterable: The iterable to collect results from
    Return:
        ``Trampoline`` of collected results
    """
    return cast(Trampoline[Iterable[A]], sequence_(Done, iterable))


@curry
def filter_(f: Callable[[A], Trampoline[bool]],
            iterable: Iterable[A]) -> Trampoline[Iterable[A]]:
    """
    Map each element in ``iterable`` by applying ``f``,
    filter the results by the value returned by ``f``
    and combine from left to right.

    Example:
        >>> filter_m(lambda v: Done(v % 2 == 0), range(3)).run()
        (0, 2)

    Args:
        f: Function to map ``iterable`` by
        iterable: Iterable to map by ``f``
    Return:
        `iterable` mapped and filtered by `f`
    """
    return cast(Trampoline[Iterable[A]], filter_m_(Done, f, iterable))


__all__ = [
    'Trampoline',
    'Done',
    'Call',
    'AndThen',
    'for_each',
    'sequence',
    'filter_', ]
