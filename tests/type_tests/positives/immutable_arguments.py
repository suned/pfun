from pfun import Immutable


class C(Immutable):  # type: ignore
    a: int


C(1)
