from zen import Maybe, Nothing, identity


def test_just() -> Maybe[int]:
    return Maybe.pure(1) | (lambda a: a * 2)


def test_nothing() -> Maybe[int]:
    return Nothing() | identity
