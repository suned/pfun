from . import maybe


@maybe.do
def f() -> maybe.Do[int, str]:
    a = yield maybe.Just(1)
    b = yield maybe.Just(2)
    return str(a + b)


reveal_type(f)
