from typing import Generic, TypeVar, Callable, cast, Any, Iterable, cast
from abc import ABC, abstractmethod

from .immutable import Immutable
from .monad import Monad, sequence_, map_m_, filter_m_
from .curry import curry

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')


class Trampoline(Immutable, Generic[A], Monad, ABC):
    @abstractmethod
    def resume(self) -> 'Trampoline[A]':
        pass

    def and_then(self, f: Callable[[A], 'Trampoline[B]']) -> 'Trampoline[B]':
        return AndThen(self, f)  # type: ignore

    def map(self, f: Callable[[A], B]) -> 'Trampoline[B]':
        return self.and_then(lambda a: Done(f(a)))

    def run(self) -> A:
        trampoline = self
        while not isinstance(trampoline, Done):
            trampoline = trampoline.resume()

        return trampoline.a


class Done(Trampoline[A]):
    a: A

    def resume(self) -> Trampoline[A]:
        return self


class Call(Trampoline[A]):
    thunk: Callable[[], Trampoline[A]]

    def resume(self) -> Trampoline[A]:
        return self.thunk()  # type: ignore


class AndThen(Generic[A, B], Trampoline[A]):
    sub: Trampoline[A]
    cont: Callable[[A], Trampoline[B]]

    def resume(self) -> Trampoline[A]:
        sub = self.sub
        cont = self.cont
        if isinstance(sub, Done):
            return cont(sub.a)  # type: ignore
        elif isinstance(sub, Call):
            return sub.thunk().and_then(cont)  # type: ignore
        else:
            sub = cast(AndThen[Any, A], sub)
            sub2 = sub.sub
            cont2 = sub.cont
        return sub2.and_then(lambda x: cont2(x).and_then(cont))  # type: ignore

    def and_then(  # type: ignore
        self,
        f: Callable[[A], Trampoline[B]]
    ) -> Trampoline[B]:
        return AndThen(  # type: ignore
            self.sub, lambda x: self.cont(x).and_then(f)  # type: ignore
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
