from typing import TypeVar, Generic, Callable

from pfun.immutable import Immutable
from abc import ABC, abstractmethod

A = TypeVar('A')
B = TypeVar('B')


class Functor(ABC):
    @abstractmethod
    def map(self, f):
        pass


C = TypeVar('C')
D = TypeVar('D')


class FreeInterpreter(Generic[C, D], ABC):
    def interpret(self, root: 'FreeInterpreterElement[C, D]', arg: C) -> D:
        return root.accept(self, arg)

    def interpret_more(self, more, arg):
        return more.k.accept(self, arg)

    def interpret_done(self, done, arg):
        return arg


class FreeInterpreterElement(Functor, Generic[C, D], ABC):
    @abstractmethod
    def accept(self, interpreter: FreeInterpreter[C, D], arg: C) -> D:
        pass


F = TypeVar('F', bound=Functor)


class Free(Generic[F, A, C, D], FreeInterpreterElement[C, D], ABC, Immutable):
    @abstractmethod
    def and_then(self,
                 f: 'Callable[[A], Free[F, B, C, D]]') -> 'Free[F, B, C, D]':
        pass

    def map(self, f: Callable[[A], B]) -> 'Free[F, B, C, D]':
        return self.and_then(lambda v: Done(f(v)))


class Done(Free[F, A, C, D]):
    a: A

    def and_then(self, f: Callable[[A], Free[F, B, C, D]]) -> Free[F, B, C, D]:
        return f(self.a)

    def accept(self, interpreter: FreeInterpreter[C, D], arg: C) -> D:
        return interpreter.interpret_done(self, arg)


class More(Free[F, A, C, D]):
    k: FreeInterpreterElement[C, D]

    def and_then(self, f: Callable[[A], Free[F, B, C, D]]) -> Free[F, B, C, D]:
        return More(self.k.map(lambda v: v.and_then(f)))

    def accept(self, interpreter: FreeInterpreter[C, D], arg: C) -> D:
        return interpreter.interpret_more(self, arg)
