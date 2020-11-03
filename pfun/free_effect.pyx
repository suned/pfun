import asyncio


cdef class Effect:
    cdef bint is_done(self):
        return False

    async def __call__(self, object r):
        effect = await self.do(r)
        if isinstance(effect, Success):
            return effect.result
        raise RuntimeError(effect.reason)
    
    async def do(self, r):
        cdef Effect effect = self
        while not effect.is_done():
            effect = (<Effect?>await effect.resume(r))
        return effect


    def and_then(self, f):
        if asyncio.iscoroutinefunction(f):
            return self.c_and_then(f)
        else:
            async def g(x):
                return f(x)
            return self.c_and_then(g)

    cdef Effect c_and_then(self, object f):
        return AndThen.__new__(AndThen, self, f)

    def map(self, f):
        async def g(x):
            result = f(x)
            if asyncio.iscoroutine(result):
                result = await result
            return Success.__new__(Success, result)

        return self.c_and_then(g)

    async def resume(self, object r):
        raise NotImplementedError()

    async def apply_continuation(self, object f, object r):
        raise NotImplementedError()
    
    def discard_and_then(self, Effect effect):
        async def g(x):
            return effect
        return self.c_and_then(g)


cdef class Success(Effect):
    cdef readonly object result

    cdef bint is_done(self):
        return True

    def __cinit__(self, result):
        self.result = result

    async def resume(self, object r):
        return self

    async def apply_continuation(self, object f, object r):
        return await f(self.result)


cdef class Error(Effect):
    cdef readonly object reason

    cdef bint is_done(self):
        return True

    def __cinit__(self, reason):
        self.reason = reason

    async def resume(self, object r):
        return self

    async def apply_continuation(self, object f, object r):
        return self


cdef class AndThen(Effect):
    cdef Effect effect
    cdef object continuation

    def __cinit__(self, effect, continuation):
        self.effect = effect
        self.continuation = continuation

    async def apply_continuation(self, object f, object r):
        return self.effect.c_and_then(self.continuation).c_and_then(f)

    async def resume(self, object r):
        return await self.effect.apply_continuation(self.continuation, r)

    cdef Effect c_and_then(self, f):
        async def g(v):
            async def thunk():
                cdef Effect e = await self.continuation(v)
                return e.c_and_then(f)
            return Call.__new__(Call, thunk)
        return AndThen.__new__(AndThen, self.effect, g)


cdef class Call(Effect):
    cdef object thunk

    def __cinit__(self, thunk):
        self.thunk = thunk

    async def resume(self, object r):
        return await self.thunk()

    async def apply_continuation(self, object f, r):
        cdef Effect effect = await self.thunk()
        return effect.c_and_then(f)


cdef class Depend(Effect):
    async def resume(self, object r):
        return Success(r)

    async def apply_continuation(self, object f, object r):
        return await f(r)

cdef Effect combine(Effect es, Effect e):
    async def f(list xs):
        async def g(object x):
            xs.append(x)
            return Success.__new__(Success, xs)

        return AndThen.__new__(AndThen, e, g)
    return AndThen.__new__(AndThen, es, f)


cpdef Effect sequence(effects):
    cdef Effect result = Success([])
    cdef Effect effect
    for effect in effects:
        result = combine(result, effect)
    return result.map(tuple)


cdef class FromAwaitable(Effect):
    cdef object awaitable

    def __cinit__(self, awaitable):
        self.awaitable = awaitable
    
    async def resume(self, object r):
        return Success.__new__(Success, await self.awaitable)
    
    async def apply_continuation(self, object f, object r):
        return f(await self.awaitable)


def from_awaitable(awaitable):
    return FromAwaitable(awaitable)


cdef class SequenceAsync(Effect):
    cdef tuple effects

    def __cinit__(self, effects):
        self.effects = effects

    async def sequence(self, object r):
        async def thunk():
            cdef Effect effect
            aws = [effect.do(r) for effect in self.effects]
            effects = await asyncio.gather(*aws)
            return sequence(effects)
        return Call.__new__(Call, thunk)

    async def resume(self, object r):
        return await self.sequence(r)

    async def apply_continuation(self, object f, object r):
        cdef Effect sequenced = await self.sequence(r)
        return sequenced.c_and_then(f)


def sequence_async(effects):
    return SequenceAsync.__new__(SequenceAsync, tuple(effects))
