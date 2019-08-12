from pfun import curry
import typing as t

A = t.TypeVar('A')


def f(a: A, b: A) -> A:
    pass


map(curry(f)(1), range(10))
