from typing import Generic, TypeVar, Callable, cast, Iterable, cast
from abc import ABC, abstractmethod

from .immutable import Immutable
from .monad import Monad, sequence_, map_m_, filter_m_
from .curry import curry

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')


class Trampoline(Immutable, Generic[A], Monad, ABC):
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
        return AndThen(self, f)

    def map(self, f: Callable[[A], B]) -> 'Trampoline[B]':
        return self.and_then(lambda a: Done(f(a)))

    def run(self) -> A:
        trampoline = self
        while not trampoline._is_done:
            trampoline = trampoline._resume()

        return cast(Done[A], trampoline).a


class Done(Trampoline[A]):
    a: A

    def _resume(self) -> Trampoline[A]:
        return self

    def _handle_cont(self,
                     cont: Callable[[A], Trampoline[B]]) -> Trampoline[B]:
        return cont(self.a)


class Call(Trampoline[A]):
    thunk: Callable[[], Trampoline[A]]

    def _handle_cont(self,
                     cont: Callable[[A], Trampoline[B]]) -> Trampoline[B]:
        return self.thunk().and_then(cont)  # type: ignore

    def _resume(self) -> Trampoline[A]:
        return self.thunk()  # type: ignore


class AndThen(Generic[A, B], Trampoline[B]):
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
            lambda x: self.cont(x).and_then(f)  # type: ignore
        )


@curry
def map_m(f: Callable[[A], Trampoline[B]],
          iterable: Iterable[A]) -> Trampoline[Iterable[B]]:
    return cast(Trampoline[Iterable[B]], map_m_(Done, f, iterable))


def sequence(iterable: Iterable[Trampoline[A]]) -> Trampoline[Iterable[A]]:
    return cast(Trampoline[Iterable[A]], sequence_(Done, iterable))


@curry
def filter_m(f: Callable[[A], Trampoline[bool]],
             iterable: Iterable[A]) -> Trampoline[Iterable[A]]:
    return cast(Trampoline[Iterable[A]], filter_m_(Done, f, iterable))


__all__ = [
    'Trampoline', 'Done', 'Call', 'AndThen', 'map_m', 'sequence', 'filter_m'
]
