from zen import Maybe


def test_just() -> Maybe[int]:
    return Maybe.pure('test') & Maybe.pure(1)
