from pfun import Immutable


class C(Immutable):
    a: int


c = C(1)
c.a = 1