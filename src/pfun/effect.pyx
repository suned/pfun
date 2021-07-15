"""
The pfun effect system.

Attributes:
    Success (TypeAlias): Type-alias for `Effect[object, NoReturn, TypeVar('A')]`.
    Try (TypeAlias): Type-alias for `Effect[object, TypeVar('E'), TypeVar('A')]`.
    Depends (TypeAlias): Type-alias for `Effect[TypeVar('R'), NoReturn, TypeVar('A')]`.
"""
from typing import Generic, TypeVar, NoReturn
import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import AsyncExitStack
from functools import wraps

import dill

from .either import Right, Left
from .functions import curry


cdef class RuntimeEnv:
    """
    Wraps the user supplied dependency R and supplies various utilities
    for the effect runtime such as the resource AsyncExitStack
    :attribute r: The user supplied dependency value
    :attribute exit_stack: AsyncExitStack used to enable Effect resources
    """
    cdef object r
    cdef object exit_stack
    cdef object max_processes
    cdef object max_threads
    cdef readonly object process_executor
    cdef readonly object thread_executor

    def __cinit__(self, r, exit_stack, max_processes, max_threads):
        self.r = r
        self.exit_stack = exit_stack
        self.max_processes = max_processes
        self.max_threads = max_threads
        self.process_executor = None
        self.thread_executor = None
    
    async def run_in_process_executor(self, f, *args, **kwargs):
        loop = asyncio.get_running_loop()
        payload = dill.dumps((f, args, kwargs))
        if self.process_executor is None:
            self.process_executor = ProcessPoolExecutor(max_workers=self.max_processes)
            self.exit_stack.enter_context(self.process_executor)
        return dill.loads(
            await loop.run_in_executor(
                self.process_executor, run_dill_encoded, payload
            )
        )

    async def run_in_thread_executor(self, f, *args, **kwargs):
        loop = asyncio.get_running_loop()
        if self.thread_executor is None:
            self.thread_executor = ThreadPoolExecutor(max_workers=self.max_threads)
            self.exit_stack.enter_context(self.thread_executor)
        return await loop.run_in_executor(
            self.thread_executor, lambda: f(*args, **kwargs)
        )


def run_dill_encoded(payload):
    fun, args, kwargs = dill.loads(payload)
    return dill.dumps(fun(*args, **kwargs))


cdef class AsyncWrapper:
    cdef object f

    def __cinit__(self, f):
        self.f = f
    
    def __repr__(self):
        return repr(self.f)
    
    async def __call__(self, *args, **kwargs):
        return self.f(*args, **kwargs)


cdef class CEffect:
    """
    Represents a side-effect
    """
    cdef bint is_done(self):
        return False
    
    def with_repr(self, repr_):
        return WithRepr(self, repr_)

    async def __call__(self, object r, max_processes=None, max_threads=None):
        """
        Run the function wrapped by this `Effect` asynchronously, \
        including potential side-effects. If the function fails the \
        resulting error will be raised as an exception.
        Args:
            self (Effect[R, E, A]):
            r (R): The dependency with which to run this `Effect`
            max_processes (Optional[int]): The max number of processes used to run cpu bound \
                parts of this effect
            max_threads (Optional[int]): The max number of threads used to run io bound \
                parts of this effect
        Return:
            Awaitable[A]: The succesful result of the wrapped function if it succeeds
        Raises:
            E: If the Effect fails and `E` is a subclass of `Exception`
            RuntimeError: if the effect fails and `E` is not a subclass of \
                          Exception
        """
        stack = AsyncExitStack()
        async with stack:
            env = RuntimeEnv(r, stack, max_processes, max_threads)
            effect = await self.do(env)
            if isinstance(effect, CSuccess):
                return effect.result
            if isinstance(effect.reason, Exception):
                raise effect.reason
            raise RuntimeError(effect.reason)
    
    async def do(self, RuntimeEnv env):
        cdef CEffect effect = self
        while not effect.is_done():
            effect = (<CEffect?>await effect.resume(env))
        return effect

    def and_then(self, f):
        """
        Create new `Effect` that applies `f` to the result of \
        running this effect successfully. If this `Effect` fails, \
        `f` is not applied.
        Example:
            >>> success(2).and_then(lambda i: success(i + 2)).run(None)
            4
        Arguments:
            self (Effect[R, E, A]):
            f (A -> Effect[Any, E2, B]): Function to pass the result of this `Effect` \
            instance once it can be computed
        Returns:
            Effect[Any, Union[E, E2], B]: New `Effect` which wraps the result of \
            passing the result of this `Effect` instance to `f`
        """
        if asyncio.iscoroutinefunction(f):
            return self.c_and_then(f)
        else:
            g = AsyncWrapper(f)
            return self.c_and_then(g)

    cdef CEffect c_and_then(self, object f):
        return AndThen.__new__(AndThen, self, f)

    def map(self, f):
        """
        Map `f` over the result produced by this `Effect` once it is run
        Example:
            >>> success(2).map(lambda v: v + 2).run(None)
            4
        Args:
            self (Effect[R, E, A]):
            f (A -> B): function to map over this `Effect`
        Return:
            Effect[R, E, B]: new `Effect` with `f` applied to the \
            value produced by this `Effect`.
        """
        return Map(self, f)
    
    def run(self, env, max_processes=None, max_threads=None):
        """
        Run the function wrapped by this `Effect`, including potential \
        side-effects. If the function fails the resulting error will be \
        raised as an exception.
        Args:
            self (Effect[R, E, A]):
            r (R): The dependency with which to run this `Effect`
            max_processes (Optional[int]): The max number of processes used to run cpu bound \
                parts of this effect
            max_threads (Optional[int]): The max number of threads used to run io bound \
                parts of this effect
        Return:
            A: The succesful result of the wrapped function if it succeeds
        Raises:
            E: If the Effect fails and `E` is a subclass of `Exception`
            RuntimeError: if the effect fails and `E` is not a subclass of \
                          Exception
        """
        return asyncio.run(self(env, max_processes, max_threads))

    async def resume(self, RuntimeEnv env):
        raise NotImplementedError()

    async def apply_continuation(self, object f, RuntimeEnv env):
        cdef CEffect effect = await self.resume(env)
        return effect.c_and_then(f)
    
    def discard_and_then(self, CEffect effect):
        """
        Create a new effect that discards the result of this effect, \
        and produces instead ``effect``. Like ``and_then`` but does not require
        you to handle the result. \
        Convenient for effects that produce ``None``, like writing to files.
        Example:
            >>> from pfun import files
            >>> class Env:
            ...     files = files.Files()
            >>> files.write('foo.txt', 'Hello!')\\
            ...     .discard_and_then(files.read('foo.txt'))\\
            ...     .run(Env())
            Hello!
        Args:
            self (Effect[R, E, A]):
            effect (Effect[Any, E2, B]): `Effect` instance to run after this `Effect` \
            has run successfully.
        Return:
            Effect[Any, Union[E, E2], B]: New effect that succeeds with `effect`
        """
        async def g(x):
            return effect
        return self.c_and_then(g).with_repr(f'{repr(self)}.discard_and_then({repr(effect)})')
    
    def either(self):
        """
        Push the potential error into the success channel as an either, \
        allowing error handling.
        Example:
            >>> error('Whoops!').either().map(
            ...     lambda either: either.get if isinstance(either, Right)
            ...                    else 'Phew!'
            ... ).run(None)
            'Phew!'
        Args:
            self (Effect[R, E, A]):
        Return:
            Effect[R, NoReturn, Either[E, A]]: New `Effect` that produces a `Left[E]` if it \
            has failed, or a :`Right[A]` if it succeeds
        """
        return Either(self)
    
    def recover(self, f):
        """
        Create new `Effect` that applies `f` to the error result of \
        running this effect if it fails. If this `Effect` succeeds, \
        ``f`` is not applied.
        Example:
            >>> error('Whoops!').recover(lambda _: success('Phew!')).run(None)
            'Phew!'
        Args:
            self (Effect[R, E, A]):
            f (E -> Effect[Any, E2, B]): Function to pass the error result of this `Effect` \
            instance once it can be computed
        Return:
            Effect[Any, E2, Union[A, B]]: New :`Effect` which wraps the result of \
            passing the error result of this `Effect` instance to `f`
        """
        return Recover(self, f)
    
    def memoize(self):
        """
        Create an `Effect` that caches its result. When the effect is evaluated
        for the second time, its side-effects are not performed, it simply
        succeeds with the cached result. This means you should be careful with
        memoizing complicated effects. Useful for effects that have expensive
        results, such as calling a slow HTTP api or reading a large file.
        Example:
            >>> from pfun.console import Console
            >>> console = Console()
            >>> effect = console.print(
            ...     'Doing something expensive'
            ... ).discard_and_then(
            ...     success('result')
            ... ).memoize()
            >>> # this would normally cause an effect to be run twice.
            >>> double_effect = effect.discard_and_then(effect)
            >>> double_effect.run(None)
            Doing something expensive
            'result'
        Args:
            self (Effect[R, E, A]):
        Return:
            Effect[R, E, A]: memoized `Effect`
        """
        return Memoize(self)
    
    def ensure(self, effect):
        """
        Create an `Effect` that will always run `effect`, regardless
        of whether this `Effect` succeeds or fails. The result of
        `effect` is ignored, and the resulting effect instead succeeds or fails
        with the succes or error value of this effect. Useful for closing
        resources.
        Example:
            >>> from pfun.effect.console import Console
            >>> console = Console()
            >>> finalizer = console.print('finalizing!')
            >>> success('result').ensure(finalizer).run(None)
            finalizing!
            'result'
            >>> error('whoops!').ensure(finalizer).run(None)
            finalizing!
            RuntimeError: whoops!
        Args:
            self (Effect[R, E, A]):
            effect (Effect[Any, NoReturn, Any]): `Effect` to run after this effect terminates \
            either successfully or with an error
        Return:
            Effect[Any, E, A]: `Effect` that fails or succeeds with the result of \
            this effect, but always runs `effect`
        """
        return self.and_then(
            lambda value: effect.
            discard_and_then(success(value))
        ).recover(
            lambda reason: effect.
            discard_and_then(error(reason))
        ).with_repr(f'{repr(self)}.ensure({repr(effect)})')


cdef class WithRepr(CEffect):
    cdef CEffect effect
    cdef object repr_

    def __cinit__(self, effect, repr_):
        self.effect = effect
        self.repr_ = repr_
    
    def __repr__(self):
        return self.repr_
    
    async def resume(self, RuntimeEnv env):
        return await self.effect.resume(env)
    
    async def apply_continuation(self, object f, RuntimeEnv env):
        return await self.effect.apply_continuation(f, env)


cdef class Memoize(CEffect):
    cdef CEffect effect
    cdef CEffect result

    def __cinit__(self, effect):
        self.effect = effect
        self.result = None
    
    def __repr__(self):
        return f'{repr(self.effect)}.memoize()'

    async def resume(self, RuntimeEnv env):
        async def thunk():
            if self.result is None:
                self.result = await self.effect.do(env)
            return self.result
        return Call(thunk)
    
    async def apply_continuation(self, object f, RuntimeEnv env):
        cdef CEffect effect = await self.resume(env)
        return effect.c_and_then(f)


cdef class Recover(CEffect):
    cdef CEffect effect
    cdef object f

    def __cinit__(self, effect, f):
        self.effect = effect
        self.f = f
    
    def __repr__(self):
        return f'{repr(self.effect)}.recover({repr(self.f)})'
    
    async def resume(self, RuntimeEnv env):
        async def thunk():
            cdef CEffect effect = await self.effect.do(env)
            if isinstance(effect, CSuccess):
                return effect
            return self.f(effect.reason)
        return Call(thunk)
    
    async def apply_continuation(self, object f, RuntimeEnv env):
        cdef CEffect effect = await self.resume(env)
        return effect.c_and_then(f)


cdef class Either(CEffect):
    cdef CEffect effect

    def __cinit__(self, effect):
        self.effect = effect
    
    def __repr__(self):
        return f'{repr(self.effect)}.either()'
    
    async def resume(self, RuntimeEnv env):
        async def thunk():
            result = await self.effect.do(env)
            if isinstance(result, CSuccess):
                return CSuccess(Right(result.result))
            return CSuccess(Left(result.reason))
        return Call(thunk)
    
    async def apply_continuation(self, object f, RuntimeEnv env):
        cdef CEffect effect = await self.resume(env)
        return effect.c_and_then(f)


cdef class ResourceGet(CEffect):
    cdef Resource resource

    def __cinit__(self, resource):
        self.resource = resource

    async def resume(self, RuntimeEnv env):
        if self.resource.resource is None:
            # this is the first time this effect is called
            resource = self.resource.resource_factory()  # type:ignore
            if asyncio.iscoroutine(resource):
                resource = await resource
            self.resource.resource = resource
            await env.exit_stack.enter_async_context(self.resource)
        if isinstance(self.resource.resource, Right):
            return CSuccess(self.resource.resource.get)
        return Error(self.resource.resource.get)
    
    async def apply_continuation(self, object f, RuntimeEnv env):
        cdef CEffect effect = await self.resume(env)
        return effect.c_and_then(f)


cdef class Resource:
    """
    Enables lazy initialisation of global async context managers that should \
    only be entered once per effect invocation. If the same resource is \
    acquired twice by an effect using `get`, the same context manager will \
    be returned. All context managers controlled by resources are guaranteed \
    to be entered before the effect that requires it is invoked, and exited \
    after it returns. The wrapped context manager is only available when the \
    resources context is entered.
    :example:
    >>> from pfun.either import Right
    >>> from aiohttp import ClientSession
    >>> resource = Resource(lambda: Right(ClientSession()))
    >>> r1, r2 = resource.get().and_then(
    ...     lambda r1: resource.get().map(lambda r2: (r1, r2))
    ... )
    >>> assert r1 is r2
    >>> assert r1.closed
    :attribute resource_factory: function to initialiaze the context manager
    """
    cdef object resource_factory
    cdef readonly object resource

    def __cinit__(self, resource_factory):
        self.resource_factory = resource_factory
        self.resource = None

    def get(self):
        """
        Create an ``Effect` that produces the initialized
        context manager.
        :example:
        >>> from aiohttp import ClientSession
        >>> resource = Resource(ClientSession)
        >>> async def get_request(session: ClientSession) -> bytes:
        ...     async with session.get('foo.com') as request:
        ...         return await request.read()
        >>> resource.get().map(get_request)(None)
        b'content of foo.com'
        :return: ``Effect`` that produces the wrapped context manager
        """
        return ResourceGet(self)

    async def __aenter__(self):
        if isinstance(self.resource, Right):
            return await self.resource.get.__aenter__()

    async def __aexit__(self, *args, **kwargs):
        resource = self.resource
        self.resource = None
        if isinstance(resource, Right):
            return await resource.get.__aexit__(*args, **kwargs)


cdef class CSuccess(CEffect):
    cdef readonly object result

    cdef bint is_done(self):
        return True

    def __cinit__(self, result):
        self.result = result
    
    def __repr__(self):
        return f'success({repr(self.result)})'

    async def resume(self, RuntimeEnv env):
        return self

    async def apply_continuation(self, object f, RuntimeEnv env):
        return await f(self.result)


def success(result):
    """
    Wrap a function in `Effect` that does nothing but return ``value``
    Example:
        >>> success('Yay!').run(None)
        'Yay!'
    Args:
        value (A): The value to return when the `Effect` is executed
    Return:
        Success[A]: Effect that wraps a function returning ``value``
    """
    return CSuccess(result)


cdef class Error(CEffect):
    cdef readonly object reason

    cdef bint is_done(self):
        return True

    def __cinit__(self, reason):
        self.reason = reason
    
    def __repr__(self):
        return f'error({repr(self.reason)})'

    async def resume(self, RuntimeEnv env):
        return self

    async def apply_continuation(self, object f, RuntimeEnv env):
        return self


def error(reason):
    """
    Create an `Effect` that does nothing but fail with `reason`
    Example:
        >>> error('Whoops!').run(None)
        RuntimeError: 'Whoops!'
    Args:
        reason (E): Value to fail with
    Return:
        Effect[object, E, NoReturn]: `Effect` that fails with `reason`
    """
    return Error(reason)


cdef class AndThen(CEffect):
    cdef CEffect effect
    cdef object continuation

    def __cinit__(self, effect, continuation):
        self.effect = effect
        self.continuation = continuation
    
    def __repr__(self):
        return f'{repr(self.effect)}.and_then({repr(self.continuation)})'

    async def apply_continuation(self, object f, RuntimeEnv env):
        return self.effect.c_and_then(self.continuation).c_and_then(f)

    async def resume(self, RuntimeEnv env):
        return await self.effect.apply_continuation(self.continuation, env)

    cdef CEffect c_and_then(self, f):
        async def g(v):
            async def thunk():
                cdef CEffect e = await self.continuation(v)
                return e.c_and_then(f)
            return Call.__new__(Call, thunk)
        return AndThen.__new__(AndThen, self.effect, g)


cdef class Map(CEffect):
    cdef CEffect effect
    cdef object continuation

    def __cinit__(self, effect, continuation):
        self.effect = effect
        self.continuation = continuation
    
    def __repr__(self):
        return f'{repr(self.effect)}.map({repr(self.continuation)})'
    
    async def resume(self, RuntimeEnv env):
        async def g(x):
            result = self.continuation(x)
            if asyncio.iscoroutine(result):
                result = await result
            return CSuccess.__new__(CSuccess, result)
        return await self.effect.apply_continuation(g, env)
    
    async def apply_continuation(self, f, RuntimeEnv env):
        cdef CEffect effect = await self.resume(env)
        return await effect.apply_continuation(f, env)


cdef class Call(CEffect):
    cdef object thunk

    def __cinit__(self, thunk):
        self.thunk = thunk

    async def resume(self, RuntimeEnv env):
        return await self.thunk()

    async def apply_continuation(self, object f, RuntimeEnv env):
        cdef CEffect effect = await self.thunk()
        return effect.c_and_then(f)


cdef class CDepends(CEffect):
    async def resume(self, RuntimeEnv env):
        return CSuccess(env.r)

    async def apply_continuation(self, object f, RuntimeEnv env):
        return await f(env.r)
    
    def __repr__(self):
        return 'depend()'


def depend(r_type=None):
    """
    Get an `Effect` that produces the dependency passed to `run` \
    when executed
    Example:
        >>> depend(str).run('dependency')
        'dependency'
    Args:
        r_type (R): The expected dependency type of the resulting effect. \
        Used ONLY for type-checking and doesn't impact runtime behaviour in \
        any way
    Return:
        Effect[R, NoReturn, R]: `Effect` that produces the dependency passed to `run`
    """
    return CDepends()


cdef class Sequence(CEffect):
    cdef tuple effects

    def __cinit__(self, effects):
        self.effects = effects
    
    def __repr__(self):
        return f'sequence({repr(self.effects)})'

    async def resume(self, RuntimeEnv env):
        async def thunk():
            cdef list result = [None]*len(self.effects)
            cdef CEffect e
            cdef CEffect e2
            cdef int i = 0
            for e in self.effects:
                e2 = await e.do(env)
                if isinstance(e2, CSuccess):
                    result[i] = e2.result
                else:
                    return e2
                i += 1
            return CSuccess(tuple(result))
        return Call(thunk)
    
    async def apply_continuation(self, object f, RuntimeEnv env):
        cdef CEffect effect = await self.resume(env)
        return effect.c_and_then(f)


cpdef CEffect sequence(effects):
    """
    Evaluate each `Effect` in `iterable`
    and collect the results
    Example:
        >>> sequence([success(v) for v in range(3)]).run(None)
        (0, 1, 2)
    Args:
        iterable (Iterable[Effect[R, E, A]]): The iterable to collect results from
    Return:
        Effect[R, E, Iterable[A]]: `Effect` that produces collected results
    """
    return Sequence(tuple(effects))


cdef class FromAwaitable(CEffect):
    cdef object awaitable

    def __cinit__(self, awaitable):
        self.awaitable = awaitable
    
    def __repr__(self):
        return f'from_awaitable({repr(self.awaitable)})'
    
    async def resume(self, RuntimeEnv env):
        return CSuccess.__new__(CSuccess, await self.awaitable)
    
    async def apply_continuation(self, object f, RuntimeEnv env):
        return f(await self.awaitable)


def from_awaitable(awaitable):
    """
    Create an `Effect` that produces the result of awaiting `awaitable`
    Example:
        >>> async def f() -> str:
        ...     return 'Yay!'
        >>> from_awaitable(f()).run(None)
        'Yay'
    Args:
        awaitable (Awaitable[A]): Awaitable to await in the resulting `Effect`
    Return:
        Success[A]: `Effect` that produces the result of awaiting `awaitable`
    """
    return FromAwaitable(awaitable)


cdef class FromCallable(CEffect):
    cdef object f

    def __cinit__(self, f):
        self.f = f
    
    def __repr__(self):
        return f'from_callable({repr(self.f)})'

    async def call_f(self, RuntimeEnv env):
        either = self.f(env.r)
        if asyncio.iscoroutine(either):
            either = await either
        return either
    
    async def resume(self, RuntimeEnv env):
        either = await self.call_f(env)
        if isinstance(either, Right):
            return CSuccess(either.get)
        return Error(either.get)
    
    async def apply_continuation(self, object f, RuntimeEnv env):
        cdef CEffect effect = await self.resume(env)
        return effect.c_and_then(f)


def from_callable(f):
    """
    Create an `Effect` from a function that takes a dependency and returns \
    an `Either`
    Example:
        >>> from pfun.either import Either, Left, Right
        >>> def f(r: str) -> Either[str, str]:
        ...     if not r:
        ...         return Left('Empty string')
        ...     return Right(r * 2)
        >>> effect = from_callable(f)
        >>> effect.run('')
        RuntimeError: Empty string
        >>> effect.run('Hello!')
        Hello!Hello!
    Args:
        f (R -> Either[E, A]): the function to turn into an `Effect`
    Return:
        Effect[R, E, A]: `f` as an `Effect`
    """
    return FromCallable(f)


cdef class FromIOBoundCallable(FromCallable):
    async def call_f(self, RuntimeEnv env):
        return await env.run_in_thread_executor(self.f, env.r)
    
    def __repr__(self):
        return f'from_io_bound_callable({repr(self.f)})'


cdef class FromCPUBoundCallable(FromCallable):
    async def call_f(self, RuntimeEnv env):
        return await env.run_in_process_executor(self.f, env.r)

    def __repr__(self):
        return f'from_cpu_bound_callable({repr(self.f)})'


def from_io_bound_callable(f):
    """
    Create an `Effect` from an io bound function that takes a dependency and returns \
    an `Either`
    Example:
        >>> from pfun.either import Either, Left, Right
        >>> def f(r: str) -> Either[str, str]:
        ...     if not r:
        ...         return Left('Empty string')
        ...     return Right(r * 2)
        >>> effect = from_io_bound_callable(f)
        >>> effect.run('')
        RuntimeError: Empty string
        >>> effect.run('Hello!')
        Hello!Hello!
    Args:
        f (R -> Either[E, A]): the function to turn into an `Effect`
    Return:
        Effect[R, E, A]: `f` as an `Effect`
    """
    if asyncio.iscoroutinefunction(f):
        raise ValueError(
            f'argument to from_io_bound_callable must not be async, got: {repr(f)}'
        )
    return FromIOBoundCallable(f)


def from_cpu_bound_callable(f):
    """
    Create an `Effect` from a cpu bound function that takes a dependency and returns \
    an `Either`
    Example:
        >>> from pfun.either import Either, Left, Right
        >>> def f(r: str) -> Either[str, str]:
        ...     if not r:
        ...         return Left('Empty string')
        ...     return Right(r * 2)
        >>> effect = from_cpu_bound_callable(f)
        >>> effect.run('')
        RuntimeError: Empty string
        >>> effect.run('Hello!')
        Hello!Hello!
    Args:
        f (R -> Either[E, A]): the function to turn into an `Effect`
    Return:
        Effect[R, E, A]: `f` as an `Effect`
    """
    if asyncio.iscoroutinefunction(f):
        raise ValueError(
            f'argument to from_io_bound_callable must not be async, got: {repr(f)}'
        )
    return FromCPUBoundCallable(f)


cdef class Catch(CEffect):
    cdef tuple exceptions
    cdef object f
    cdef tuple args
    cdef object kwargs

    def __cinit__(self, exceptions, f, args, kwargs):
        self.exceptions = exceptions
        self.f = f
        self.args = args
        self.kwargs = kwargs
    
    def __repr__(self):
        es_repr = ', '.join([repr(e) for e in self.exceptions])
        args_repr = ', '.join([repr(a) for a in self.args])
        kwargs_repr = ', '.join([f'{repr(name)}={repr(a)}' for name, a in self.kwargs.items()])
        sig_repr = args_repr
        sig_repr = sig_repr + ', ' + kwargs_repr if kwargs_repr else sig_repr
        return f'catch({es_repr})({repr(self.f)})({sig_repr})'
    
    async def call_f(self, RuntimeEnv env):
        result = self.f(*self.args, **self.kwargs)
        if asyncio.iscoroutine(result):
            result = await result
        return result

    async def resume(self, RuntimeEnv env):
        try:
            result = await self.call_f(env)
            return CSuccess(result)
        except Exception as e:
            if any(isinstance(e, e_type) for e_type in self.exceptions):
                return Error(e)
            raise e
    
    async def apply_continuation(self, object f, RuntimeEnv env):
        cdef CEffect effect = await self.resume(env)
        return effect.c_and_then(f)


def catch(exception, *exceptions):
    """
    Decorator that catches errors as an `Effect`. If the decorated
    function performs additional side-effects, they are not carried out
    until the effect is run.
    Example:
        >>> f = catch(ZeroDivisionError)(lambda v: 1 / v)
        >>> f(1).run(None)
        1.0
        >>> f(0).run(None)
        ZeroDivisionError
    Args:
        exception (Exception): The first exception to catch
        exceptions (Exception): Remaining exceptions to catch
    Returns:
        ((*args, **kwargs) -> A) -> Effect[object, Exception, A]: Decorator of functions \
            that handle expection arguments as an `Effect`.
    """
    def decorator1(f):
        @wraps(f)
        def decorator2(*args, **kwargs):
            return Catch((exception,) + exceptions, f, args, kwargs)
        return decorator2
    return decorator1


cdef class CatchIOBound(Catch):
    async def call_f(self, RuntimeEnv env):
        return await env.run_in_thread_executor(self.f, *self.args, **self.kwargs)
    
    def __repr__(self):
        es_repr = ', '.join([repr(e) for e in self.exceptions])
        args_repr = ', '.join([repr(a) for a in self.args])
        kwargs_repr = ', '.join([f'{repr(name)}={repr(a)}' for name, a in self.kwargs.items()])
        sig_repr = args_repr
        sig_repr = sig_repr + ', ' + kwargs_repr if kwargs_repr else sig_repr
        return f'catch_io_bound({es_repr})({repr(self.f)})({sig_repr})'
    

cdef class CatchCPUBound(Catch):
    async def call_f(self, RuntimeEnv env):
        return await env.run_in_process_executor(self.f, *self.args, **self.kwargs)
    
    def __repr__(self):
        es_repr = ', '.join([repr(e) for e in self.exceptions])
        args_repr = ', '.join([repr(a) for a in self.args])
        kwargs_repr = ', '.join([f'{repr(name)}={repr(a)}' for name, a in self.kwargs.items()])
        sig_repr = args_repr
        sig_repr = sig_repr + ', ' + kwargs_repr if kwargs_repr else sig_repr
        return f'catch_cpu_bound({es_repr})({repr(self.f)})({sig_repr})'

def catch_io_bound(exception, *exceptions):
    """
    Decorator that catches errors from an io bound function as an `Effect`. If the decorated
    function performs additional side-effects, they are not carried out
    until the effect is run.
    Example:
        >>> f = catch_io_bound(ZeroDivisionError)(lambda v: 1 / v)
        >>> f(1).run(None)
        1.0
        >>> f(0).run(None)
        ZeroDivisionError
    Args:
        exception (Exception): The first exception to catch
        exceptions (Exception): Remaining exceptions to catch
    Returns:
        ((*args, **kwargs) -> A) -> Effect[object, Exception, A]: Decorator of functions \
            that handle expection arguments as an `Effect`.
    """
    def decorator1(f):
        if asyncio.iscoroutinefunction(f):
            raise ValueError(
                f'argument to catch_io_bound must not be async, got: {repr(f)}'
            )
        @wraps(f)
        def decorator2(*args, **kwargs):
            return CatchIOBound((exception,) + exceptions, f, args, kwargs)
        return decorator2
    return decorator1


def catch_cpu_bound(exception, *exceptions):
    """
    Decorator that catches errors from a cpu bound function as an `Effect`. If the decorated
    function performs additional side-effects, they are not carried out
    until the effect is run.
    Example:
        >>> f = catch_cpu_bound(ZeroDivisionError)(lambda v: 1 / v)
        >>> f(1).run(None)
        1.0
        >>> f(0).run(None)
        ZeroDivisionError
    Args:
        exception (Exception): The first exception to catch
        exceptions (Exception): Remaining exceptions to catch
    Returns:
        ((*args, **kwargs) -> A) -> Effect[object, Exception, A]: Decorator of functions \
            that handle expection arguments as an `Effect`.
    """
    def decorator1(f):
        if asyncio.iscoroutinefunction(f):
            raise ValueError(
                f'argument to catch_cpu_bound must not be async, got: {repr(f)}'
            )
        @wraps(f)
        def decorator2(*args, **kwargs):
            return CatchCPUBound((exception,) + exceptions, f, args, kwargs)
        return decorator2
    return decorator1


cdef class SequenceAsync(CEffect):
    cdef tuple effects

    def __cinit__(self, effects):
        self.effects = effects
    
    def __repr__(self):
        return f'sequence_async({repr(self.effects)})'

    async def sequence(self, object r):
        async def thunk():
            cdef CEffect effect
            cdef list aws = [None]*len(self.effects)
            cdef int i = 0
            for effect in self.effects:
                aws[i] = effect.do(r)
                i += 1
            effects = await asyncio.gather(*aws)
            return sequence(effects)
        return Call.__new__(Call, thunk)

    async def resume(self, RuntimeEnv env):
        return await self.sequence(env)

    async def apply_continuation(self, object f, RuntimeEnv env):
        cdef CEffect sequenced = await self.sequence(env)
        return sequenced.c_and_then(f)


def sequence_async(effects):
    """
    Evaluate each `Effect` in `iterable` asynchronously
    and collect the results
    Example:
        >>> sequence_async([success(v) for v in range(3)]).run(None)
        (0, 1, 2)
    Args:
        iterable (Iterable[Effect[R, E, A]]): The iterable to collect results from
    Return:
        Effect[R, E, Iterable[A]]: `Effect` that produces collected results
    """
    return SequenceAsync.__new__(SequenceAsync, tuple(effects))


def lift(f):
    """
    Decorator that enables decorated functions to operate on `Effect`
    instances. Note that the returned function does not accept keyword arguments.
    Example:
        >>> def add(a: int, b: int) -> int:
        ...     return a + b
        >>> lift(add)(success(2), success(2)).run(None)
        4
    Args:
        f ( (*A, **B) -> C): The function to decorate
    Returns:
        (*Effect[R, E, A] -> Effect[R, E, C]): The decorated function
    """
    @wraps(f)
    def decorator(*effects):
        effect = sequence(effects)
        args_repr = ', '.join(repr(e) for e in effects)
        return effect.map(lambda xs: f(*xs)).with_repr(f'lift({repr(f)})({args_repr})')
    return decorator

cdef class LiftIOBound(CEffect):
    cdef object f
    cdef object effects

    def __cinit__(self, f, effects):
        self.f = f
        self.effects = effects
    
    def __repr__(self):
        args_repr = ', '.join(repr(e) for e in self.effects)
        return f'lift_io_bound({self.f})({args_repr})'

    async def resume(self, RuntimeEnv env):
        async def call_f(xs):
            return await env.run_in_thread_executor(self.f, *xs)
        effect = sequence(self.effects)
        return effect.map(call_f)

def lift_io_bound(f):
    """
    Decorator that enables decorated io bound functions to operate on `Effect`
    instances. Note that the returned function does not accept keyword arguments.
    Example:
        >>> def add(a: int, b: int) -> int:
        ...     return a + b
        >>> lift_io_bound(add)(success(2), success(2)).run(None)
        4
    Args:
        f ( (*A, **B) -> C): The function to decorate
    Returns:
        (*Effect[R, E, A] -> Effect[R, E, C]): The decorated function
    """
    if asyncio.iscoroutinefunction(f):
        raise ValueError(
            f'argument to lift_io_bound must not be async, got: {repr(f)}'
        )
    @wraps(f)
    def decorator(*effects):
        return LiftIOBound(f, effects)
    return decorator


cdef class LiftCPUBound(CEffect):
    cdef object f
    cdef object effects

    def __cinit__(self, f, effects):
        self.f = f
        self.effects = effects
    
    def __repr__(self):
        args_repr = ', '.join(repr(e) for e in self.effects)
        return f'lift_cpu_bound({self.f})({args_repr})'

    async def resume(self, RuntimeEnv env):
        async def call_f(xs):
            return await env.run_in_process_executor(self.f, *xs)
        effect = sequence(self.effects)
        return effect.map(call_f)

def lift_cpu_bound(f):
    """
    Decorator that enables decorated cpu bound functions to operate on `Effect`
    instances. Note that the returned function does not accept keyword arguments.
    Example:
        >>> def add(a: int, b: int) -> int:
        ...     return a + b
        >>> lift_cpu_bound(add)(success(2), success(2)).run(None)
        4
    Args:
        f ( (*A, **B) -> C): The function to decorate
    Returns:
        (*Effect[R, E, A] -> Effect[R, E, C]): The decorated function
    """
    if asyncio.iscoroutinefunction(f):
        raise ValueError(
            f'argument to lift_cpu_bound must not be async, got: {repr(f)}'
        )
    @wraps(f)
    def decorator(*effects):
        return LiftCPUBound(f, effects)
    return decorator

def combine(*effects):
    """
    Create an effect that produces the result of calling the passed function \
    with the results of effects in `effects`
    Example:
        >>> combine(success(2), success(2))(lambda a, b: a + b).run(None)
        4
    Args:
        effects (Effect[R, E, A]): Effects the results of which to pass to the combiner \
        function
    Return:
        (((*A, **B) -> C) -> *Effect[R, E, A] -> Effect[R, E, C]): function that takes a combiner function and returns an \
        `Effect` that applies the function to the results of `effects`
    """
    def f(g):
        args_repr = ', '.join(repr(e) for e in effects)
        return lift(g)(*effects).with_repr(f'combine({args_repr})({repr(g)})')
    return f


def combine_cpu_bound(*effects):
    """
    Create an effect that produces the result of calling the passed cpu bound function \
    with the results of effects in `effects`
    Example:
        >>> combine_cpu_bound(success(2), success(2))(lambda a, b: a + b).run(None)
        4
    Args:
        effects (Effect[R, E, A]): Effects the results of which to pass to the combiner \
        function
    Return:
        (((*A, **B) -> C) -> *args: Effect[R, E, A] -> Effect[R, E, C]): function that takes a combiner function and returns an \
        `Effect` that applies the function to the results of `effects`
    """
    def f(g):
        args_repr = ', '.join(repr(e) for e in effects)
        return lift_cpu_bound(g)(*effects).with_repr(f'combine_cpu_bound({args_repr})({repr(g)})')
    return f


def combine_io_bound(*effects):
    """
    Create an effect that produces the result of calling the passed io bound function \
    with the results of effects in `effects`
    Example:
        >>> combine_io_bound(success(2), success(2))(lambda a, b: a + b).run(None)
        4
    Args:
        effects (Effect[R, E, A]): Effects the results of which to pass to the combiner \
        function
    Return:
        (((*A, **B) -> C) -> *args: Effect[R, E, A] -> Effect[R, E, C]): function that takes a combiner function and returns an \
        `Effect` that applies the function to the results of `effects`
    """
    def f(g):
        args_repr = ', '.join(repr(e) for e in effects)
        return lift_io_bound(g)(*effects).with_repr(f'combine_io_bound({args_repr})({repr(g)})')
    return f


@curry
def filter_(f, iterable):
    """
    Map each element in ``iterable`` by applying ``f``,
    filter the results by the value returned by ``f``
    and combine from left to right.
    Example:
        >>> filter(lambda v: success(v % 2 == 0), range(3)).run(None)
        (0, 2)
    Args:
        f (A -> Effect[R, E, bool]): Function to map ``iterable`` by
        iterable (Iterable[A]): Iterable to map by ``f``
    Return:
        Effect[R, E, Iterable[A]]: `iterable` mapped and filtered by `f`
    """
    iterable = tuple(iterable)
    bools = sequence(f(a) for a in iterable)
    return bools.map(
        lambda bs: tuple(a for b, a in zip(bs, iterable) if b)
    ).with_repr(
        f'filter_({repr(f)})({repr(iterable)})'
    )


@curry
def for_each(f, iterable):
    """
    Map each in element in ``iterable`` to
    an `Effect` by applying ``f``,
    combine the elements by ``and_then``
    from left to right and collect the results
    Example:
        >>> for_each(success, range(3)).run(None)
        (0, 1, 2)
    Args:
        f (A -> Effect[R, E, B]): Function to map over ``iterable``
        iterable (Iterable[A]): Iterable to map ``f`` over
    Return:
        Effect[R, E, Iterable[B]]: `f` mapped over `iterable` and combined from left to right.
    """
    iterable = tuple(iterable)
    return sequence(f(x) for x in iterable).with_repr(f'for_each({repr(f)})({repr(iterable)})')


def absolve(effect):
    """
    Move the error type from an `Effect` producing an `Either` \
    into the error channel of the `Effect`
    Example:
        >>> effect = error('Whoops').either().map(
        ...     lambda either: either.get if isinstance(either, Right)
        ...                    else 'Phew!'
        ... )
        >>> absolve(effect).run(None)
        'Phew!'
    Args:
        effect (Effect[R, NoReturn, Either[E, A]]): an `Effect` producing an `Either`
    Return:
        Effect[R, E, A]: an `Effect` failing with `E` or succeeding with `A`
    """
    def f(either):
        if either:
            return CSuccess(either.get)
        return Error(either.get)
    return effect.and_then(f).with_repr(f'absolve({repr(effect)})')


def _get_sig_repr(args, kwargs):
    args_repr = ', '.join([repr(arg) for arg in args])
    kwargs_repr = ', '.join(
        [f'{name}={repr(value)}' for name, value in kwargs.items()]
    )
    return args_repr + ((', ' + kwargs_repr) if kwargs_repr else '')


def add_repr(f):
    """
    Decorator for functions that return effects that adds repr strings
    based on the function name and args.
    :example:
    >>> @add_repr
    >>> def do_something(value):
    ...     return success(value)
    >>> do_something(1)
    do_something(1)
    :param f: function to be decorated
    :return: decorated function
    """
    @wraps(f)
    def decorator(*args, **kwargs):
        effect = f(*args, **kwargs)
        sig_repr = _get_sig_repr(args, kwargs)
        repr_ = f'{f.__name__}({sig_repr})'
        return effect.with_repr(repr_)

    return decorator


def add_method_repr(f):
    """
    Decorator for methods that return effects that add repr strings based
    on the class, method and args.
    :example:
    >>> from pfun import Immutable
    >>> class Foo(Immutable):
    ...     @add_method_repr
    ...     def do_something(value):
    ...         return success(value)
    >>> Foo().do_something(1)
    Foo().do_something(1)
    :param f: the method to be decorated
    :return: decorated method
    """
    @wraps(f)
    def decorator(*args, **kwargs):
        effect = f(*args, **kwargs)
        self, *args = args
        sig_repr = _get_sig_repr(args, kwargs)
        repr_ = f'{repr(self)}.{f.__name__}({sig_repr})'
        return effect.with_repr(repr_)

    return decorator  # type: ignore


R = TypeVar('R', contravariant=True)
A = TypeVar('A', covariant=True)
E = TypeVar('E', covariant=True)


EffectGen = Generic[R, E, A]


class Effect(CEffect, *EffectGen.__mro_entries__((EffectGen,))):
    __orig_bases__ = (EffectGen,)


Success = Effect[object, NoReturn, A]
Try = Effect[object, E, A]
Depends = Effect[R, NoReturn, A]


__all__ = [
    'Effect',
    'Success',
    'Try',
    'Depends',
    'success',
    'depend',
    'sequence_async',
    'sequence',
    'filter_',
    'for_each',
    'absolve',
    'error',
    'lift',
    'lift_io_bound',
    'lift_cpu_bound',
    'combine',
    'combine_io_bound',
    'combine_cpu_bound',
    'catch',
    'catch_io_bound',
    'catch_cpu_bound',
    'from_awaitable',
    'from_callable',
    'from_io_bound_callable',
    'from_cpu_bound_callable'
]
