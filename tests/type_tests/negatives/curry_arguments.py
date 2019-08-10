from pfun import curry


@curry
def f(a: int, b: int) -> str:
    pass


f(1)('')