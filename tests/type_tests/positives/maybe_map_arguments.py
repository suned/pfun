from pfun.maybe import Maybe, Nothing, Just


def test_just() -> Maybe[str]:
    return Just('test').map(lambda a: a.lower())


def test_nothing() -> Maybe[str]:
    return Nothing().map(lambda a: a.lower())
