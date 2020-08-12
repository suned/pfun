class Effect:
    def __call__(self, r):
        effect = self
        while not isinstance(effect, Success) or isinstance(effect, Error):
            effect = effect.resume(r)
        if isinstance(effect, Success):
            return effect.result
        raise RuntimeError(effect.reason)

    def and_then(self, f):
        return AndThen(self, f)

    def map(self, f):
        return self.and_then(lambda v: Success(f(v)))

    def resume(self, r):
        raise NotImplementedError()

    def apply_continuation(self, f, r):
        raise NotImplementedError()


class Success(Effect):
    def __init__(self, result):
        self.result = result

    def resume(self, r):
        return self

    def apply_continuation(self, f, r):
        return f(self.result)


class Error(Effect):
    def __init__(self, reason):
        self.reason = reason

    def resume(self, r):
        return self

    def apply_continuation(self, f, r):
        return self


class AndThen(Effect):
    def __init__(self, effect, continuation):
        self.effect = effect
        self.continuation = continuation

    def apply_continuation(self, f, r):
        return self.effect.and_then(self.continuation).and_then(f)

    def resume(self, r):
        return self.effect.apply_continuation(self.continuation, r)

    def and_then(self, f):
        return AndThen(
            self.effect,
            lambda x: Call(lambda: self.continuation(x).and_then(f))
        )


class Call(Effect):
    def __init__(self, thunk):
        self.thunk = thunk

    def resume(self, r):
        return self.thunk()

    def apply_continuation(self, f, r):
        return self.thunk().and_then(f)


class Depend(Effect):
    def resume(self, r):
        return Success(r)

    def apply_continuation(self, f, r):
        return f(r)


def sequence(effects):
    result = Success([])
    for effect in effects:
        result = result.and_then(lambda xs: effect.map(lambda x: (xs.append(x), xs)[1]))
    return result.map(tuple)
