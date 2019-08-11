from pfun import curry


class C:
    def __call__(a):
        pass


class D(C):
    pass

reveal_type(curry(D()))
