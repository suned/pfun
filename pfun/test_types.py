from pfun.maybe import do, Just, Nothing, Do


@do
def f(x) -> Do[int, int]:
    l = []
    for _ in range(x):
        a = yield Just(1)
        l.append(a)
    a = yield Nothing()
    return sum(l)
