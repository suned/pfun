from zen import Maybe, Just


def test_just() -> Maybe[str]:
    return Just(1).and_then(lambda a: str(a))
