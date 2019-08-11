from pfun import curry


class C:
    def __call__(self, a: int, b: int) -> int:
        pass


c = curry(C())


c('')('') + 1
