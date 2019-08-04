from zen import Maybe, Just


def test() -> Maybe[str]:
	return Just(1).map(lambda a: a.lower())
