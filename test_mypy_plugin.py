from typing import overload
from pfun import curry


def f(a: int, b: str) -> int:
    pass


reveal_type(curry(f))
