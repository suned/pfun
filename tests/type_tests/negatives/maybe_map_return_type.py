from zen import Maybe, Just


def test_just() -> Maybe[int]:
	return Just(1).map(str)
