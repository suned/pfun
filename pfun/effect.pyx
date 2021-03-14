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
    cdef object process_executor
    cdef object thread_executor

    def __cinit__(self, r, exit_stack, process_executor, thread_executor):
        self.r = r
        self.exit_stack = exit_stack
        self.process_executor = process_executor
        self.thread_executor = thread_executor
    
    async def run_in_process_executor(self, f, *args, **kwargs):
        loop = asyncio.get_running_loop()
        payload = dill.dumps((f, args, kwargs))
        return dill.loads(
            await loop.run_in_executor(
                self.process_executor, run_dill_encoded, payload
            )
        )

    async def run_in_thread_executor(self, f, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self.thread_executor, lambda: f(*args, **kwargs)
        )


def run_dill_encoded(payload):
    fun, args, kwargs = dill.loads(payload)
    return dill.dumps(fun(*args, **kwargs))


cdef class Effect:
    """
    Represents a side-effect
    """
    cdef bint is_done(self):
        return False

    async def __call__(self, object r):
        """
        Run the function wrapped by this `Effect` asynchronously, \
        including potential side-effects. If the function fails the \
        resulting error will be raised as an exception.
        Args:
            r: The dependency with which to run this `Effect`
            max_processes: The max number of processes used to run cpu bound \
                parts of this effect
            max_threads: The max number of threads used to run io bound \
                parts of this effect
        Return:
            The succesful result of the wrapped function if it succeeds
        Raises:
            E: If the Effect fails and `E` is a subclass of `Exception`
            RuntimeError: if the effect fails and `E` is not a subclass of \
                          Exception
        """
        stack = AsyncExitStack()
        process_executor = ProcessPoolExecutor()
        thread_executor = ThreadPoolExecutor()
        async with stack:
            stack.enter_context(process_executor)
            stack.enter_context(thread_executor)
            env = RuntimeEnv(r, stack, process_executor, thread_executor)
            effect = await self.do(env)
            if isinstance(effect, Success):
                return effect.result
            if isinstance(effect.reason, Exception):
                raise effect.reason
            raise RuntimeError(effect.reason)
    
    async def do(self, RuntimeEnv env):
        cdef Effect effect = self
        while not effect.is_done():
            effect = (<Effect?>await effect.resume(env))
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
            f: Function to pass the result of this `Effect` \
            instance once it can be computed
        Returns:
            New `Effect` which wraps the result of \
            passing the result of this `Effect` instance to `f`
        """
        if asyncio.iscoroutinefunction(f):
            return self.c_and_then(f)
        else:
            async def g(x):
                return f(x)
            return self.c_and_then(g)

    cdef Effect c_and_then(self, object f):
        return AndThen.__new__(AndThen, self, f)

    def map(self, f):
        """
        Map `f` over the result produced by this `Effect` once it is run
        Example:
            >>> success(2).map(lambda v: v + 2).run(None)
            4
        Args:
            f: function to map over this `Effect`
        Return:
            new `Effect` with `f` applied to the \
            value produced by this `Effect`.
        """
        async def g(x):
            result = f(x)
            if asyncio.iscoroutine(result):
                result = await result
            return Success.__new__(Success, result)

        return self.c_and_then(g)
    
    def run(self, env):
        """
        Run the function wrapped by this `Effect`, including potential \
        side-effects. If the function fails the resulting error will be \
        raised as an exception.
        Args:
            r: The dependency with which to run this `Effect` \
            asyncio_run: Function to run the coroutine returned by the \
            wrapped function
            max_processes: The max number of processes used to run cpu bound \
                parts of this effect
            max_threads: The max number of threads used to run io bound \
                parts of this effect
        Return:
            The succesful result of the wrapped function if it succeeds
        Raises:
            E: If the Effect fails and `E` is a subclass of `Exception`
            RuntimeError: if the effect fails and `E` is not a subclass of \
                          Exception
        """
        return asyncio.run(self(env))

    async def resume(self, RuntimeEnv env):
        raise NotImplementedError()

    async def apply_continuation(self, object f, RuntimeEnv env):
        raise NotImplementedError()
    
    def discard_and_then(self, Effect effect):
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
            effect: `Effect` instance to run after this `Effect` \
            has run successfully.
        Return:
            New effect that succeeds with `effect`
        """
        async def g(x):
            return effect
        return self.c_and_then(g)
    
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
        Return:
            New `Effect` that produces a `Left[E]` if it \
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
            f: Function to pass the error result of this `Effect` \
            instance once it can be computed
        Return:
            New :`Effect` which wraps the result of \
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
        Return:
            memoized `Effect`
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
            effect: `Effect` to run after this effect terminates \
            either successfully or with an error
        Return:
            `Effect` that fails or succeeds with the result of \
            this effect, but always runs `effect`
        """
        return self.and_then(
            lambda value: effect.
            discard_and_then(success(value))
        ).recover(
            lambda reason: effect.
            discard_and_then(error(reason))
        )


cdef class Memoize(Effect):
    cdef Effect effect
    cdef Effect result

    def __cinit__(self, effect):
        self.effect = effect
        self.result = None

    async def resume(self, RuntimeEnv env):
        async def thunk():
            if self.result is None:
                self.result = await self.effect.do(env)
            return self.result
        return Call(thunk)
    
    async def apply_continuation(self, object f, RuntimeEnv env):
        cdef Effect effect = await self.resume(env)
        return effect.c_and_then(f)


cdef class Recover(Effect):
    cdef Effect effect
    cdef object f

    def __cinit__(self, effect, f):
        self.effect = effect
        self.f = f
    
    async def resume(self, RuntimeEnv env):
        async def thunk():
            cdef Effect effect = await self.effect.do(env)
            if isinstance(effect, Success):
                return effect
            return self.f(effect.reason)
        return Call(thunk)
    
    async def apply_continuation(self, object f, RuntimeEnv env):
        cdef Effect effect = self.resume(env)
        return effect.c_and_then(f)


cdef class Either(Effect):
    cdef Effect effect

    def __cinit__(self, effect):
        self.effect = effect
    
    async def resume(self, RuntimeEnv env):
        async def thunk():
            result = await self.effect.do(env)
            if isinstance(result, Success):
                return Success(Right(result.result))
            return Success(Left(result.reason))
        return Call(thunk)
    
    async def apply_continuation(self, object f, RuntimeEnv env):
        cdef Effect effect = self.resume(env)
        return effect.c_and_then(f)




cdef class ResourceGet(Effect):
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
            return Success(self.resource.resource.get)
        return Error(self.resource.resource.get)
    
    async def apply_continuation(self, object f, RuntimeEnv env):
        cdef Effect effect = await self.resume(env)
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


cdef class Success(Effect):
    cdef readonly object result

    cdef bint is_done(self):
        return True

    def __cinit__(self, result):
        self.result = result

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
        value: The value to return when the `Effect` is executed
    Return:
        `Effect` that wraps a function returning ``value``
    """
    return Success(result)


cdef class Error(Effect):
    cdef readonly object reason

    cdef bint is_done(self):
        return True

    def __cinit__(self, reason):
        self.reason = reason

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
        reason: Value to fail with
    Return:
        `Effect` that fails with `reason`
    """
    return Error(reason)


cdef class AndThen(Effect):
    cdef Effect effect
    cdef object continuation

    def __cinit__(self, effect, continuation):
        self.effect = effect
        self.continuation = continuation

    async def apply_continuation(self, object f, RuntimeEnv env):
        return self.effect.c_and_then(self.continuation).c_and_then(f)

    async def resume(self, RuntimeEnv env):
        return await self.effect.apply_continuation(self.continuation, env)

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

    async def resume(self, RuntimeEnv env):
        return await self.thunk()

    async def apply_continuation(self, object f, RuntimeEnv env):
        cdef Effect effect = await self.thunk()
        return effect.c_and_then(f)


cdef class Depends(Effect):
    async def resume(self, RuntimeEnv env):
        return Success(env.r)

    async def apply_continuation(self, object f, RuntimeEnv env):
        return await f(env.r)

cdef Effect c_combine(Effect es, Effect e):
    async def f(list xs):
        async def g(object x):
            xs.append(x)
            return Success.__new__(Success, xs)

        return AndThen.__new__(AndThen, e, g)
    return AndThen.__new__(AndThen, es, f)


def depend(r_type=None):
    """
    Get an `Effect` that produces the dependency passed to `run` \
    when executed
    Example:
        >>> depend(str).run('dependency')
        'dependency'
    Args:
        r_type: The expected dependency type of the resulting effect. \
        Used ONLY for type-checking and doesn't impact runtime behaviour in \
        any way
    Return:
        `Effect` that produces the dependency passed to `run`
    """
    return Depends()


cpdef Effect sequence(effects):
    cdef Effect result = Success([])
    cdef Effect effect
    for effect in effects:
        result = c_combine(result, effect)
    return result.map(tuple)


cdef class FromAwaitable(Effect):
    cdef object awaitable

    def __cinit__(self, awaitable):
        self.awaitable = awaitable
    
    async def resume(self, RuntimeEnv env):
        return Success.__new__(Success, await self.awaitable)
    
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
        awaitable: Awaitable to await in the resulting `Effect`
    Return:
        `Effect` that produces the result of awaiting `awaitable`
    """
    return FromAwaitable(awaitable)


cdef class FromCallable(Effect):
    cdef object f

    def __cinit__(self, f):
        self.f = f
    
    async def resume(self, RuntimeEnv env):
        either = self.f(env.r)
        if asyncio.iscoroutine(either):
            either = await either
        if isinstance(either, Right):
            return Success(either.get)
        return Error(either.get)
    
    async def apply_continuation(self, object f, RuntimeEnv env):
        cdef Effect effect = await self.resume(env)
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
        f: the function to turn into an `Effect`
    Return:
        `f` as an `Effect`
    """
    return FromCallable(f)


cdef class Catch(Effect):
    cdef tuple exceptions
    cdef object f
    cdef tuple args
    cdef object kwargs

    def __cinit__(self, exceptions, f, args, kwargs):
        self.exceptions = exceptions
        self.f = f
        self.args = args
        self.kwargs = kwargs
    
    async def resume(self, RuntimeEnv env):
        try:
            result = self.f(*self.args, **self.kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            return Success(result)
        except Exception as e:
            if any(isinstance(e, e_type) for e_type in self.exceptions):
                return Error(e)
            raise e
    
    async def apply_continuation(self, object f, RuntimeEnv env):
        cdef Effect effect = self.resume(env)
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
    """
    def decorator1(f):
        @wraps(f)
        def decorator2(*args, **kwargs):
            return Catch((exception,) + exceptions, f, args, kwargs)
        return decorator2
    return decorator1



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

    async def resume(self, RuntimeEnv env):
        return await self.sequence(env)

    async def apply_continuation(self, object f, RuntimeEnv env):
        cdef Effect sequenced = await self.sequence(env)
        return sequenced.c_and_then(f)


def sequence_async(effects):
    """
    Evaluate each `Effect` in `iterable` asynchronously
    and collect the results
    Example:
        >>> sequence_async([success(v) for v in range(3)]).run(None)
        (0, 1, 2)
    Args:
        iterable: The iterable to collect results from
    Return:
        `Effect` that produces collected results
    """
    return SequenceAsync.__new__(SequenceAsync, tuple(effects))


def lift(f):
    """
    Decorator that enables decorated functions to operate on `Effect`
    instances.
    Example:
        >>> def add(a: int, b: int) -> int:
        ...     return a + b
        >>> lift(add)(success(2), success(2)).run(None)
        4
    """
    @wraps(f)
    def decorator(*effects):
        effect = sequence(effects)
        return effect.map(lambda xs: f(*xs))
    return decorator

def combine(*effects):
    """
    Create an effect that produces the result of calling the passed function \
    with the results of effects in `effects`
    Example:
        >>> combine(success(2), success(2))(lambda a, b: a + b).run(None)
        4
    Args:
        effects: Effects the results of which to pass to the combiner \
        function
    Return:
        function that takes a combiner function and returns an \
        `Effect` that applies the function to the results of `effects`
    """
    def f(g):
        effect = sequence(effects)
        return effect.map(lambda xs: g(*xs))
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
        f: Function to map ``iterable`` by
        iterable: Iterable to map by ``f``
    Return:
        `iterable` mapped and filtered by `f`
    """
    iterable = tuple(iterable)
    bools = sequence(f(a) for a in iterable)
    return bools.map(lambda bs: tuple(a for b, a in zip(bs, iterable) if b))


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
        f: Function to map over ``iterable``
        iterable: Iterable to map ``f`` over
    Return:
        `f` mapped over `iterable` and combined from left to right.
    """
    return sequence(f(x) for x in iterable)


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
        effect: an `Effect` producing an `Either`
    Return:
        an `Effect` failing with `E1` or succeeding with `A1`
    """
    def f(either):
        if isinstance(either, Right):
            return Success(either.get)
        return Error(either.get)
    return effect.and_then(f)


def add_repr(f):
    return f

def add_method_repr(f):
    return f

class Try:
    pass

def io_bound(f):
    return f

def cpu_bound(f):
    return f


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
    'combine',
    'lift',
    'catch',
    'from_awaitable',
    'from_callable',
    'cpu_bound',
    'io_bound'
]
