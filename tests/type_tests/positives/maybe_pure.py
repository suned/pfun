from zen import Maybe


def test() -> Maybe[int]:
    return Maybe.pure(1)
