from pfun import compose


def f(a: int) -> int:
    pass


def g(a: int) -> int:
    pass


h = compose(f, g)

map(h, range(5))
