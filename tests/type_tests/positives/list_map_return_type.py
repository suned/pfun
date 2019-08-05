from pfun import List


def test() -> List[int]:
    return List(i for i in (1, 2, 3)).map(lambda x: x**2)
