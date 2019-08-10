from pfun import List


def test() -> List[int]:
    return List([1]).map(str).map(lambda x: x**2)
