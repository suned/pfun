from abc import ABC, abstractmethod
from typing import Callable, Generator, Generic, Iterable, TypeVar, cast

from .curry import curry
from .immutable import Immutable
from .monad import Monad, filter_m_, map_m_, sequence_
from .with_effect import with_effect_

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

        :param f: function to apply the value in this trampoline
        :return: Result of applying ``f`` to the value wrapped by \
            this trampoline
        """
        return AndThen(self, f)

    def map(self, f: Callable[[A], B]) -> 'Trampoline[B]':
        """
        Map ``f`` over the value wrapped by this trampoline.

        :param f: function to wrap over this trampoline
        :return: new trampoline wrapping the result of ``f``
        """
        return self.and_then(lambda a: Done(f(a)))

    def run(self) -> A:
        """
        Interpret a structure of trampolines to produce a result

        :return: result of intepreting this structure of \
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
def map_m(f: Callable[[A], Trampoline[B]],
          iterable: Iterable[A]) -> Trampoline[Iterable[B]]:
    """
    Map each in element in ``iterable`` to
    an :class:`Trampoline` by applying ``f``,
    combine the elements by ``and_then``
    from left to right and collect the results

    :example:
    >>> map_m(Just, range(3))
    Just((0, 1, 2))

    :param f: Function to map over ``iterable``
    :param iterable: Iterable to map ``f`` over
    :return: ``f`` mapped over ``iterable`` and combined from left to right.
    """
    return cast(Trampoline[Iterable[B]], map_m_(Done, f, iterable))


def sequence(iterable: Iterable[Trampoline[A]]) -> Trampoline[Iterable[A]]:
    """
    Evaluate each :class:`Trampoline` in `iterable` from left to right
    and collect the results

    :example:
    >>> sequence([Just(v) for v in range(3)])
    Just((0, 1, 2))

    :param iterable: The iterable to collect results from
    :returns: ``Trampoline`` of collected results
    """
    return cast(Trampoline[Iterable[A]], sequence_(Done, iterable))


@curry
def filter_m(f: Callable[[A], Trampoline[bool]],
             iterable: Iterable[A]) -> Trampoline[Iterable[A]]:
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
    return cast(Trampoline[Iterable[A]], filter_m_(Done, f, iterable))


Trampolines = Generator[Trampoline[A], A, B]


def with_effect(f: Callable[..., Trampolines[A, B]]
                ) -> Callable[..., Trampoline[B]]:
    """
    Decorator for functions that
    return a generator of trampolines and a final result.
    Iteraters over the yielded trampolines and sends back the
    unwrapped values using "and_then"

    :example:
    >>> @with_effect
    ... def f() -> Trampolines[int, int]:
    ...     a = yield Done(2)
    ...     b = yield Done(2)
    ...     return a + b
    >>> f()
    Done(4)

    :param f: generator function to decorate
    :return: `f` decorated such that generated :class:`Trampoline` \
        will be chained together with `and_then`
    """
    return with_effect_(Done, f)  # type: ignore


__all__ = [
    'Trampoline',
    'Done',
    'Call',
    'AndThen',
    'map_m',
    'sequence',
    'filter_m',
    'Trampolines',
    'with_effect'
]
