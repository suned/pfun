from .immutable import Immutable
from typing import Generic, TypeVar, Callable, cast

A = TypeVar('A')
B = TypeVar('B')


class Trampoline(Immutable, Generic[A]):
    def and_then(self, f):
        return AndThen(self, f)


class Done(Trampoline[A]):
    a: A


class Call(Trampoline[A]):
    thunk: Callable[[], Trampoline[A]]


class AndThen(Generic[A, B], Trampoline[A]):
    sub: Trampoline[A]
    cont: Callable[[A], Trampoline[B]]

    
    def and_then(self, f):
        return AndThen(self.sub, lambda x: self.cont(x).and_then(f))



def run(trampoline: Trampoline[A]) -> A:
    while not isinstance(trampoline, Done):
        if isinstance(trampoline, Call):
            trampoline = trampoline.thunk()  # type: ignore
        else:
            sub = trampoline.sub
            cont = trampoline.cont
            if isinstance(sub, Done):
                trampoline = cont(sub.a)  # type: ignore
            elif isinstance(sub, Call):
                trampoline = sub.thunk().and_then(cont)  # type: ignore
            else:
                sub2 = sub.sub
                cont2 = sub.cont
                trampoline = sub2.and_then(lambda x: cont2(x).and_then(cont))
    return trampoline.a
