from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from functools import wraps
from typing import (Any, AsyncContextManager, Awaitable, Callable, Generic,
                    Iterable, NoReturn, Optional, Type, TypeVar, Union,
                    overload)

from .aio_trampoline import Call, Done, Trampoline
from .aio_trampoline import sequence as sequence_trampolines
from .either import Either, Left, Right
from .either import sequence as sequence_eithers
from .functions import curry
from .immutable import Immutable

R = TypeVar('R', contravariant=True)
E = TypeVar('E', covariant=True)
E2 = TypeVar('E2')
A = TypeVar('A', covariant=True)
B = TypeVar('B')

C = TypeVar('C', bound=AsyncContextManager)

F = TypeVar('F', bound=Callable[..., 'Effect'])


def add_repr(f: F) -> F:
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
        args_repr = ', '.join([repr(arg) for arg in args])
        kwargs_repr = ', '.join(
            [f'{name}={repr(value)}' for name, value in kwargs.items()]
        )
        sig_repr = args_repr + ((', ' + kwargs_repr) if kwargs_repr else '')
        repr_ = f'{f.__name__}({sig_repr})'
        return effect.with_repr(repr_)

    return decorator  # type: ignore


def add_method_repr(f: F) -> F:
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
        args_repr = ', '.join([repr(arg) for arg in args])
        kwargs_repr = ', '.join(
            [f'{name}={repr(value)}' for name, value in kwargs.items()]
        )
        sig_repr = args_repr + ((', ' + kwargs_repr) if kwargs_repr else '')
        repr_ = f'{repr(self)}.{f.__name__}({sig_repr})'
        return effect.with_repr(repr_)

    return decorator  # type: ignore


class Resource(Immutable, Generic[E, C]):
    """
    Enables lazy initialisation of global async context managers that should \
    only be entered once per effect invocation. If the same resource is \
    acquired twice by an effect using `get`, the same context manager will \
    be returned. All context managers controlled by resources are guaranteed \
    to be entered before the effect that requires it is invoked, and exited \
    after it returns. The wrapped context manager is only available when the \
    resources context is entered.


    :example:
    >>> from aiohttp import ClientSession
    >>> resource = Resource(ClientSession)
    >>> r1, r2 = resource.get().and_then(
    ...     lambda r1: resource.get().map(lambda r2: (r1, r2))
    ... )
    >>> assert r1 is r2
    >>> assert r1.closed
    >>> assert resource.resource is None

    :attribute resource_factory: function to initialiaze the context manager
    """
    resource_factory: Callable[[],
                               Union[Either[E, C], Awaitable[Either[E, C]]]]
    resource: Optional[Either[E, C]] = None

    def get(self) -> Effect[object, E, C]:
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
        async def run_e(env: RuntimeEnv):
            if self.resource is None:
                # this is the first time this effect is called
                resource = self.resource_factory()  # type:ignore
                if asyncio.iscoroutine(resource):
                    resource = await resource
                object.__setattr__(self, 'resource', resource)
                await env.exit_stack.enter_async_context(self)
            return Done(self.resource)

        return Effect(run_e)

    async def __aenter__(self):
        if isinstance(self.resource, Right):
            return await self.resource.get.__aenter__()

    async def __aexit__(self, *args, **kwargs):
        resource = self.resource
        object.__setattr__(self, 'resource', None)
        if isinstance(self.resource, Right):
            return await resource.get.__aexit__(*args, **kwargs)


class RuntimeEnv(Immutable, Generic[A]):
    """
    Wraps the user supplied environment R and supplies various utilities
    for the effect runtime such as the resource AsyncExitStack

    :attribute r: The user supplied environment value
    :attribute exit_stack: AsyncExitStack used to enable Effect resources
    """
    r: A
    exit_stack: AsyncExitStack


class Effect(Generic[R, E, A], Immutable):
    """
    Wrapper for functions of type \
    `Callable[[R], Awaitable[pfun.Either[E, A]]]` that are allowed to \
    perform side-effects
    """
    run_e: Callable[[RuntimeEnv[R]], Awaitable[Trampoline[Either[E, A]]]]
    _repr: str = ''

    def with_repr(self, s: str) -> Effect[R, E, A]:
        return Effect(self.run_e, s)  # type: ignore

    def __repr__(self):
        if not self._repr:
            return f'Effect(run_e={repr(self.run_e)})'

        return self._repr

    @add_method_repr
    def and_then(
        self,
        f: Callable[[A],
                    Union[Awaitable[Effect[Any, E2, B]], Effect[Any, E2, B]]]
    ) -> Effect[Any, Union[E, E2], B]:
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
        async def run_e(r: RuntimeEnv[R]
                        ) -> Trampoline[Either[Union[E, E2], B]]:
            async def thunk():
                def cont(either: Either):
                    if isinstance(either, Left):
                        return Done(either)

                    async def thunk():
                        next_ = f(either.get)
                        if asyncio.iscoroutine(next_):
                            effect = await next_
                        else:
                            effect = next_
                        return await effect.run_e(r)

                    return Call(thunk)

                trampoline = await self.run_e(r)
                return trampoline.and_then(cont)

            return Call(thunk)

        return Effect(run_e)

    @add_method_repr
    def discard_and_then(self, effect: Effect[Any, E2, B]
                         ) -> Effect[Any, Union[E, E2], B]:
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
        return self.and_then(lambda _: effect)  # type: ignore

    @add_method_repr
    def either(self) -> Effect[R, NoReturn, Either[E, A]]:
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
        async def run_e(r: RuntimeEnv[R]
                        ) -> Trampoline[Either[NoReturn, Either[E, A]]]:
            async def thunk() -> Trampoline[Either[NoReturn, Either[E, A]]]:
                trampoline = await self.run_e(r)  # type: ignore
                return trampoline.and_then(lambda either: Done(Right(either)))

            return Call(thunk)

        return Effect(run_e)

    @add_method_repr
    def recover(self, f: Callable[[E], Effect[Any, E2, B]]
                ) -> Effect[Any, E2, Union[A, B]]:
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
        async def run_e(r: RuntimeEnv[R]) -> Trampoline[Either[E2, A]]:
            async def thunk():
                def cont(either: Either):
                    if isinstance(either, Right):
                        return Done(either)

                    async def thunk():
                        next_ = f(either.get)
                        if asyncio.iscoroutine(next_):
                            effect = await next_
                        else:
                            effect = next_
                        return await effect.run_e(r)

                    return Call(thunk)

                trampoline = await self.run_e(r)
                return trampoline.and_then(cont)

            return Call(thunk)

        return Effect(run_e)

    @add_method_repr
    def ensure(self, effect: Effect[Any, NoReturn, Any]) -> Effect[Any, E, A]:
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
            lambda value: effect.  # type: ignore
            discard_and_then(success(value))
        ).recover(
            lambda reason: effect.  # type: ignore
            discard_and_then(error(reason))
        )

    async def __call__(self, r: R) -> A:  # type: ignore
        """
        Run the function wrapped by this `Effect` asynchronously, \
        including potential side-effects. If the function fails the \
        resulting error will be raised as an exception.

        Args:
            r: The environment with which to run this `Effect` \
            asyncio_run: Function to run the coroutine returned by the \
            wrapped function
        Return:
            The succesful result of the wrapped function if it succeeds

        Raises:
            E: If the Effect fails and `E` is a subclass of `Exception`
            RuntimeError: if the effect fails and `E` is not a subclass of \
                          Exception

        """
        async with AsyncExitStack() as stack:
            env = RuntimeEnv(r, stack)
            trampoline = await self.run_e(env)  # type: ignore
            result = await trampoline.run()
            if isinstance(result, Left):
                error = result.get
                if isinstance(error, Exception):
                    raise error
                else:
                    raise RuntimeError(repr(error))
            else:
                return result.get

    def run(
        self, r: R, asyncio_run: Callable[[Awaitable[A]], A] = asyncio.run
    ) -> A:
        """
        Run the function wrapped by this `Effect`, including potential \
        side-effects. If the function fails the resulting error will be \
        raised as an exception.

        Args:
            r: The environment with which to run this `Effect` \
            asyncio_run: Function to run the coroutine returned by the \
            wrapped function
        Return:
            The succesful result of the wrapped function if it succeeds
        Raises:
            E: If the Effect fails and `E` is a subclass of `Exception`
            RuntimeError: if the effect fails and `E` is not a subclass of \
                          Exception
        """

        return asyncio_run(self(r))

    @add_method_repr
    def map(self, f: Callable[[A], Union[Awaitable[B], B]]) -> Effect[R, E, B]:
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
        async def run_e(r: RuntimeEnv[R]) -> Trampoline[Either[E, B]]:
            def cont(either):
                async def thunk() -> Trampoline[Either]:
                    result = f(either.get)
                    if asyncio.iscoroutine(result):
                        result = await result  # type: ignore
                    return Done(Right(result))

                if isinstance(either, Left):
                    return Done(either)
                return Call(thunk)

            trampoline = await self.run_e(r)  # type: ignore
            return trampoline.and_then(cont)

        return Effect(run_e)


R1 = TypeVar('R1')
E1 = TypeVar('E1')
A1 = TypeVar('A1')


@add_repr
def success(value: A1) -> Effect[object, NoReturn, A1]:
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
    async def run_e(_):
        return Done(Right(value))

    return Effect(run_e)


@overload
def get_environment(r_type: None = None) -> Depends:
    pass


@overload
def get_environment(r_type: Type[R1] = None) -> Depends[R1, R1]:
    pass


def get_environment(r_type: Optional[Type[R1]] = None) -> Depends[R1, R1]:
    """
    Get an `Effect` that produces the environment passed to `run` \
    when executed

    Example:
        >>> get_environment(str).run('environment')
        'environment'

    Args:
        r_type: The expected environment type of the resulting effect. \
        Used ONLY for type-checking and doesn't impact runtime behaviour in \
        any way

    Return:
        `Effect` that produces the enviroment passed to `run`
    """
    async def run_e(env):
        return Done(Right(env.r))

    return Effect(
        run_e,
        f'get_environment({r_type.__name__ if r_type is not None else ""})'
    )


@add_repr
def from_awaitable(awaitable: Awaitable[A1]) -> Effect[object, NoReturn, A1]:
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
    async def run_e(_):
        return Done(Right(await awaitable))

    return Effect(run_e)


@add_repr
def sequence_async(iterable: Iterable[Effect[R1, E1, A1]]
                   ) -> Effect[R1, E1, Iterable[A1]]:
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
    iterable = tuple(iterable)

    async def run_e(r: RuntimeEnv[R1]):
        awaitables = [e.run_e(r) for e in iterable]  # type: ignore
        trampolines = await asyncio.gather(*awaitables)
        # TODO should this be run in an executor to avoid blocking?
        # maybe depending on the number of effects?
        trampoline = sequence_trampolines(trampolines)
        return trampoline.map(lambda eithers: sequence_eithers(eithers))

    return Effect(run_e)


@curry
@add_repr
def map_m(f: Callable[[A1], Effect[R1, E1, A1]],
          iterable: Iterable[A1]) -> Effect[R1, E1, Iterable[A1]]:
    """
    Map each in element in ``iterable`` to
    an `Effect` by applying ``f``,
    combine the elements by ``and_then``
    from left to right and collect the results

    Example:
        >>> map_m(success, range(3)).run(None)
        (0, 1, 2)

    Args:
        f: Function to map over ``iterable``
        iterable: Iterable to map ``f`` over
    Return:
        `f` mapped over `iterable` and combined from left to right.
    """
    effects = (f(x) for x in iterable)
    return sequence_async(effects)


@curry
@add_repr
def filter_m(f: Callable[[A], Effect[R1, E1, bool]],
             iterable: Iterable[A]) -> Effect[R1, E1, Iterable[A]]:
    """
    Map each element in ``iterable`` by applying ``f``,
    filter the results by the value returned by ``f``
    and combine from left to right.

    Example:
        >>> filter_m(lambda v: success(v % 2 == 0), range(3)).run(None)
        (0, 2)

    Args:
        f: Function to map ``iterable`` by
        iterable: Iterable to map by ``f``

    Return:
        `iterable` mapped and filtered by `f`
    """
    iterable = tuple(iterable)

    async def run_e(r: RuntimeEnv[R1]):
        async def thunk():
            awaitables = [f(a).run_e(r) for a in iterable]
            trampolines = await asyncio.gather(*awaitables)
            trampoline = sequence_trampolines(trampolines)
            return trampoline.map(
                lambda eithers: sequence_eithers(eithers).
                map(lambda bs: tuple(a for a, b in zip(iterable, bs) if b))
            )

        return Call(thunk)

    return Effect(run_e)


@add_repr
def absolve(effect: Effect[R1, NoReturn, Either[E1, A1]]
            ) -> Effect[R1, E1, A1]:
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
    async def run_e(r) -> Trampoline[Either[E1, A1]]:
        async def thunk():
            trampoline = await effect.run_e(r)
            return trampoline.and_then(lambda either: Done(either.get))

        return Call(thunk)

    return Effect(run_e)


@add_repr
def error(reason: E1) -> Effect[object, E1, NoReturn]:
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
    async def run_e(r):
        return Done(Left(reason))

    return Effect(run_e)


A2 = TypeVar('A2')


def combine(*effects: Effect[R1, E1, A2]
            ) -> Callable[[Callable[..., A1]], Effect[Any, Any, A1]]:
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
    def _(f: Callable[..., A1]):
        effect = sequence_async(effects)
        args_repr = ", ".join([repr(effect) for effect in effects])
        repr_ = f'combine({args_repr})({repr(f)})'
        return effect.map(lambda seq: f(*seq)).with_repr(repr_)

    return _


EX = TypeVar('EX', bound=Exception)


# @curry
def catch(error_type: Type[EX],
          ) -> Callable[[Callable[[], A1]], Effect[object, EX, A1]]:
    """
    Catch exceptions raised by a function and push them into the error type \
    of an `Effect`

    Example:
        >>> catch(ZeroDivisionError)(lambda: 1 / 0).either().run(None)
        Left(ZeroDivisionError('division by zero'))

    Args:
        error_type: Exception type to catch. All other exceptions will \
        not be handled

    Return:
        `Effect` that can fail with exceptions raised by the \
        passed function
    """
    def _(f):
        repr_ = f'catch({error_type.__name__})({repr(f)})'
        try:
            return success(f()).with_repr(repr_)
        except error_type as e:
            return error(e).with_repr(repr_)

    return _


@add_repr
def catch_all(f: Callable[[], A1]) -> Effect[object, Exception, A1]:
    """
    Return an `Effect` that can fail with any exceptions raised by `f`

    Example:
        >>> catch_all(lambda: 1 / 0).either().run(None)
        Left(ZeroDivisionError('division by zero'))

    Args:
        f: All exceptions raised by this functions will be pushed to the \
        error channel of the resulting `Effect`

    Return:
        `Effect` that cain fail with exceptions raised by `f` \
        or succeed with the result of `f`
    """
    async def run_e(_: Any) -> Trampoline[Either[Exception, A1]]:
        try:
            return Done(Right(f()))
        except Exception as e:
            return Done(Left(e))

    return Effect(run_e)


Success = Effect[object, NoReturn, A1]
"""
Type-alias for `Effect[object, NoReturn, TypeVar('A')]`.
"""
Try = Effect[object, E1, A1]
"""
Type-alias for `Effect[object, TypeVar('E'), TypeVar('A')]`.
"""
Depends = Effect[R1, NoReturn, A1]
"""
Type-alias for `Effect[TypeVar('R'), NoReturn, TypeVar('A')]`.
"""

__all__ = [
    'Effect',
    'Success',
    'Try',
    'Depends',
    'success',
    'get_environment',
    'sequence_async',
    'filter_m',
    'map_m',
    'absolve',
    'error',
    'combine',
    'catch',
    'catch_all',
    'from_awaitable'
]
