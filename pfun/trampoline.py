from .immutable import Immutable
from typing import Generic, TypeVar, Callable, cast, Any
from abc import ABC, abstractmethod

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')


class Trampoline(Immutable, Generic[A], ABC):
    @abstractmethod
    def resume(self) -> 'Trampoline[A]':
        pass

    def and_then(self, f):
        return AndThen(self, f)

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

    def and_then(self, f):
        return AndThen(self.sub, lambda x: self.cont(x).and_then(f))
