from pfun.maybe import Maybe, Nothing, Just

from typing import Any


def test_just() -> Maybe[str]:
    return Just(1).and_then(lambda a: Just(str(a)))


# todo
# def test_nothing() -> Maybe[str]:
#     return Nothing().and_then(lambda a: Just(''))
