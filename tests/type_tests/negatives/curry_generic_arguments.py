from pfun import curry
import typing as t

A = t.TypeVar('A')


def f(a: A, b: A) -> A:
    pass


g = curry(f)('')
map(g, range(10))
