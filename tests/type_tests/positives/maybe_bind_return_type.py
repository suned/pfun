from pfun.maybe import Maybe, Nothing, Just


def test_just() -> Maybe[int]:
    return Just(1).and_then(lambda a: Just(1))


def test_nothing() -> Maybe[int]:
    return Just(1).and_then(lambda a: Nothing())
