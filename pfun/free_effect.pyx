# cython: profile=True
cimport cython

from functools import reduce
import asyncio

ctypedef object (*continuation)(object)


cdef class Continuation:
    cdef object apply(self, object v):
        raise NotImplementedError()


cdef class UserContinuation(Continuation):
    cdef object f

    def __cinit__(self, f):
        self.f = f

    cdef object apply(self, object v):
        return self.f(v)

cdef class MapContinuation(Continuation):
    cdef object f

    def __cinit__(self, f):
        self.f = f

    cdef object apply(self, object v):
        return Success.__new__(Success, self.f(v))



async def try_await(v):
    try:
        return await v
    except TypeError:
        return v


@cython.trashcan(True)
cdef class Effect:
    async def __call__(self, r):
        cdef Effect effect = self
        while not isinstance(effect, Success) or isinstance(effect, Error):
            effect = (<Effect?>await try_await(effect.resume(r)))
        if isinstance(effect, Success):
            return await try_await(effect.result)
        raise RuntimeError(await try_await(effect.reason))

    def and_then(self, f):
        return self.c_and_then(UserContinuation.__new__(UserContinuation, f))
    
    cdef Effect c_and_then(self, Continuation f):
        return AndThen.__new__(AndThen, self, f)

    def map(self, f):
        return self.c_and_then(MapContinuation.__new__(MapContinuation, f))

    cdef object resume(self, object r):
        raise NotImplementedError()

    async def apply_continuation(self, Continuation f, object r):
        raise NotImplementedError()


cdef class Success(Effect):
    cdef readonly object result

    def __cinit__(self, result):
        self.result = result

    cdef object resume(self, object r):
        return self

    async def apply_continuation(self, Continuation f, object r):
        return await try_await(f.apply(await try_await(self.result)))


cdef class Error(Effect):
    cdef readonly object reason

    def __cinit__(self, reason):
        self.reason = reason

    cdef object resume(self, object r):
        return self

    async def apply_continuation(self, Continuation f, object r):
        return self

cdef class AndThenContinuation(Continuation):
    cdef Continuation continuation
    cdef Continuation f

    def __cinit__(self, continuation, f):
        self.continuation = continuation
        self.f = f

    def make_call(self, v):
        async def thunk():
            e = self.continuation.apply(v)
            cdef Effect effect = await try_await(e)
            return effect.c_and_then(self.f)
        
        return Call.__new__(Call, thunk)

    cdef object apply(self, object v):
        return self.make_call(v)

cdef class AndThen(Effect):
    cdef Effect effect
    cdef Continuation continuation

    def __cinit__(self, effect, continuation):
        self.effect = effect
        self.continuation = continuation

    async def apply_continuation(self, Continuation f, object r):
        return self.effect.and_then(self.continuation).c_and_then(f)

    cdef object resume(self, object r):
        return self.effect.apply_continuation(self.continuation, r)

    cdef Effect c_and_then(self, Continuation f):
        return AndThen.__new__(
            AndThen,
            self.effect,
            AndThenContinuation.__new__(AndThenContinuation, self.continuation, f)
        )


cdef class Call(Effect):
    cdef object thunk

    def __cinit__(self, thunk):
        self.thunk = thunk

    cdef object resume(self, object r):
        return self.thunk()

    async def apply_continuation(self, Continuation f, r):
        cdef Effect effect = await self.thunk()
        return effect.c_and_then(f)


cdef class Depend(Effect):
    cdef object resume(self, object r):
        return Success(r)

    async def apply_continuation(self, Continuation f, object r):
        return await try_await(f.apply(r))


cdef class SequenceContinuation(Continuation):
    cdef Effect e

    def __cinit__(self, e):
        self.e = e
    
    cdef object apply(self, object xs):
        return self.e.c_and_then(SequenceContinuation2.__new__(SequenceContinuation2, xs))

cdef class SequenceContinuation2(Continuation):
    cdef list xs

    def __cinit__(self, xs):
        self.xs = xs
    
    cdef object apply(self, object v):
        self.xs.append(v)
        return Success.__new__(Success, self.xs)

cpdef Effect combine(Effect es, Effect e):
    return es.c_and_then(SequenceContinuation.__new__(SequenceContinuation, e))

def sequence(effects):
    return reduce(combine, effects, Success([])).map(tuple)
