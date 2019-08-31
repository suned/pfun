from typing import Generic, TypeVar, Callable, Tuple
from .immutable import Immutable


A = TypeVar('A')
B = TypeVar('B')


class IO(Generic[A], Immutable):
    def __init__(self, a: A):
        self.a = a

    def and_then(self, f):
        return f(self.a)
    
    def run(self, world: int) -> A:
        return self.a


class Put(IO[Tuple[str, IO[A]]]):

    def and_then(self, f: Callable[[A], IO[B]]) -> IO[B]:
        text, a = self.a
        return Put((text, a.and_then(f)))