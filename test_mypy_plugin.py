from typing import TypeVar, Callable
from pfun import compose, maybe


A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')

def f(a: A) -> A:
    pass


def g(a: B) -> maybe.Maybe[B]:
    pass


def h(a: int) -> int:
    pass


reveal_type(compose(f, g))
