from pfun.reader import reader, ask


@reader
def f(b: int) -> int:
    pass


@reader
def g(r: str) -> int:
    pass


reveal_type(ask().and_then(g).and_then(f))
