from pfun.maybe import Maybe, Nothing, Just
from pfun import identity

from typing import Any


def test_just() -> Maybe[int]:
    return Just(1).map(lambda a: a * 2)


def test_nothing() -> Maybe[Any]:
    return Nothing().map(identity)
