from zen import List


def test() -> List[str]:
    return List(i for i in (1, 2, 3)).and_then(lambda x: List([x**2]))
