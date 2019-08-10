from pfun import curry


@curry
def f(a: int, b: int) -> str:
    pass


map(f(1), range(5))
