from pfun import curry


@curry
def f(a: int, b: str) -> str:
    pass


map(f(1), range(5))
