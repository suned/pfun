from pfun import compose


def f(a: int) -> str:
    pass


def g(a: str) -> int:
    pass


h = compose(f, g)

map(h, range(5))
