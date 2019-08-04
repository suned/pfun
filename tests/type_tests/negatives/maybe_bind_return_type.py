from zen import Maybe, Just


def test_just() -> Maybe[int]:
	return Just(1).and_then(lambda a: Just(''))
