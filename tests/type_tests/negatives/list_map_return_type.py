from pfun import List


def test() -> List[str]:
    return List(i for i in (1, 2, 3)).map(lambda x: x**2)
