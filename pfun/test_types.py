from . import maybe


@maybe.do
def f() -> maybe.Do[int, str]:
    a = yield maybe.Just(1)
    b = yield maybe.Just(2)
    return str(a + b)


reveal_type(f)

maybe.Just(1).and_then(lambda a: maybe.Just(2)
                       ).and_then(lambda b: maybe.Just(a + b))
