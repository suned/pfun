from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from functools import wraps
from typing import (Any, AsyncContextManager, Awaitable, Callable, Generator,
                    Generic, Iterable, NoReturn, Optional, Type, TypeVar,
                    Union)

from ..aio_trampoline import Call, Done, Trampoline
from ..aio_trampoline import sequence as sequence_trampolines
from ..curry import curry
from ..either import Either, Left, Right
from ..either import sequence as sequence_eithers
from ..immutable import Immutable

R = TypeVar('R', contravariant=True)
E = TypeVar('E', covariant=True)
E2 = TypeVar('E2')
A = TypeVar('A', covariant=True)
B = TypeVar('B')

C = TypeVar('C', bound=AsyncContextManager)


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

    def get(self) -> Effect[Any, E, C]:
        """
        Create an :class:``Effect` that produces the initialized
        context manager.

        :example:
        >>> from aiohttp import ClientSession
        >>> resource = Resource(ClientSession)
        >>> async def get_request(session: ClientSession) -> bytes:
        ...     async with session.get('foo.com') as request:
        ...         return await request.read()
        >>> resource.get().map(get_request)(None)
        b'content of foo.com'

        :return: :class:``Effect`` that produces the wrapped context manager
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
    Wrapper for functions that are allowed to perform side-effects
    """
    run_e: Callable[[RuntimeEnv[R]], Awaitable[Trampoline[Either[E, A]]]]

    def and_then(
        self,
        f: Callable[[A],
                    Union[Awaitable[Effect[Any, E2, B]], Effect[Any, E2, B]]]
    ) -> Effect[Any, Union[E, E2], B]:
        """
        Create new :class:`Effect` that applies ``f`` to the result of \
        running this effect successfully. If this :class:`Effect` fails, \
        ``f`` is not applied.

        :example:
        >>> success(2).and_then(lambda i: success(i + 2)).run(None)
        4

        :param f: Function to pass the result of this :class:`Effect` \
        instance once it can be computed

        :return: New :class:`Effect` which wraps the result of \
        passing the result of this :class:`Effect` instance to ``f``
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

    def discard_and_then(self, effect: Effect[Any, E2, B]
                         ) -> Effect[Any, Union[E, E2], B]:
        """
        Create a new effect that discards the result of this effect, \
        and produces instead ``effect``. Like ``and_then`` but does not require
        you to handle the result. \
        Convenient for effects that produce ``None``, like writing to files.

        :example:
        >>> class Env:
        ...     files = effect.files.Files()
        >>> effect.files.write('foo.txt', 'Hello!')\\
        ...     .discard_and_then(effect.files.read('foo.txt'))\\
        ...     .run(Env())
        Hello!

        :param effect: :class:`Effect` instance to run after this \
        :class:`Effect` has run successfully.

        :return: New effect that succeeds with `effect`
        """
        return self.and_then(lambda _: effect)  # type: ignore

    def either(self) -> Effect[R, NoReturn, Either[E, A]]:
        """
        Push the potential error into the success channel as an either, \
        allowing error handling.

        :example:
        >>> error('Whoops!').either().map(
        ...     lambda either: either.get if isinstance(either, Right)
        ...                    else 'Phew!'
        ... ).run(None)
        'Phew!'

        :return: New :class:`Effect` that produces a :class:`Left[E]` if it \
            has failed, or a :class:`Right[A]` if it succeeds
        """
        async def run_e(r: RuntimeEnv[R]
                        ) -> Trampoline[Either[NoReturn, Either[E, A]]]:
            async def thunk() -> Trampoline[Either[NoReturn, Either[E, A]]]:
                trampoline = await self.run_e(r)  # type: ignore
                return trampoline.and_then(lambda either: Done(Right(either)))

            return Call(thunk)

        return Effect(run_e)

    def recover(self,
                f: Callable[[E], Effect[Any, E2, A]]) -> Effect[Any, E2, A]:
        """
        Create new :class:`Effect` that applies ``f`` to the error result of \
        running this effect if it fails. If this :class:`Effect` succeeds, \
        ``f`` is not applied.

        :example:
        >>> error('Whoops!').recover(lambda _: success('Phew!')).run(None)
        'Phew!'

        :param f: Function to pass the error result of this :class:`Effect` \
        instance once it can be computed

        :return: New :class:`Effect` which wraps the result of \
        passing the error result of this :class:`Effect` instance to ``f``
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

    def ensure(self, effect: Effect[Any, NoReturn, Any]) -> Effect[R, E, A]:
        """
        Create an :class:`Effect` that will always run `effect`, regardless
        of whether this :class:`Effect` succeeds or fails. The result of
        `effect` is ignored, and the resulting effect instead succeeds or fails
        with the succes or error value of this effect. Useful for closing
        resources.

        :example:
        >>> from pfun.effect.console import Console
        >>> console = Console()
        >>> finalizer = console.print('finalizing!')
        >>> success('result').ensure(finalizer).run(None)
        finalizing!
        'result'
        >>> error('whoops!').ensure(finalizer).run(None)
        finalizing!
        RuntimeError: whoops!

        :param effect: :class:`Effect` to run after this effect terminates \
            either successfully or with an error
        :return: :class:`Effect` that fails or succeeds with the result of \
            this effect, but always runs `effect`
        """
        return self.and_then(
            lambda value: effect.  # type: ignore
            discard_and_then(success(value))
        ).recover(
            lambda reason: effect.  # type: ignore
            discard_and_then(error(reason))
        )

    def run(self, r: R, asyncio_run=asyncio.run) -> A:
        """
        Run the function wrapped by this :class:`Effect`, including potential \
        side-effects. If the function fails the resulting error will be \
        raised as an exception.

        :param r: The environment with which to run this :class:`Effect`
        :param asyncio_run: Function to run the coroutine returned by the \
            wrapped function
        :returns: The succesful result of the wrapped function if it succeeds
        """
        async def _run() -> A:  # type: ignore
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

        return asyncio_run(_run())

    __call__ = run

    def map(self, f: Callable[[A], Union[Awaitable[B], B]]) -> Effect[R, E, B]:
        """
        Map `f` over the result produced by this :class:`Effect` once it is run

        :example:
        >>> success(2).map(lambda v: v + 2).run(None)
        4

        :param f: function to map over this :class:`Effect`
        :return: new :class:`Effect` with `f` applied to the \
            value produced by this :class:`Effect`.
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


def success(value: A1) -> Effect[Any, NoReturn, A1]:
    """
    Wrap a function in :class:`Effect` that does nothing but return ``value``

    :example:
    >>> success('Yay!').run(None)
    'Yay!'

    :param value: The value to return when the :class:`Effect` is executed
    :return: :class:`Effect` that wraps a function returning ``value``
    """
    async def run_e(_):
        return Done(Right(value))

    return Effect(run_e)


def get_environment() -> Effect[Any, NoReturn, Any]:
    """
    Get an :class:`Effect` that produces the environment passed to `run` \
    when executed

    :example:
    >>> get_environment().run('environment')
    'environment'

    :return: :class:`Effect` that produces the enviroment passed to `run`
    """
    async def run_e(env):
        return Done(Right(env.r))

    return Effect(run_e)


def from_awaitable(awaitable: Awaitable[A1]) -> Effect[Any, NoReturn, A1]:
    """
    Create an :class:`Effect` that produces the result of awaiting `awaitable`

    :example:
    >>> async def f() -> str:
    ...     return 'Yay!'
    >>> from_awaitable(f()).run(None)
    'Yay'

    :param awaitable: Awaitable to await in the resulting :class:`Effect`
    :return: :class:`Effect` that produces the result of awaiting `awaitable`
    """
    async def run_e(_):
        return Done(Right(await awaitable))

    return Effect(run_e)


def decorate(
    f: Callable[[A1], Union[Awaitable[Either[E1, B1]], Either[E1, B1]]]
) -> Callable[[A1], Effect[Any, E1, B1]]:
    def _(a: A1) -> Effect[Any, E1, B1]:
        async def run_e(_):
            either = f(a)
            if asyncio.iscoroutine(either):
                either = await either
            return Done(either)

        return Effect(run_e)

    return _


B1 = TypeVar('B1')
Effects = Generator[Effect[R1, E1, Any], Any, B1]


def with_effect(f: Callable[..., Effects[R1, E1, A1]]
                ) -> Callable[..., Effect[R1, E1, A1]]:
    """
    Decorator for functions generating :class:`Effect` instances. Will
    chain together the generated effectss using `and_then`

    :example:
    >>> @with_effect
    ... def f() -> Effects[Any, NoReturn, int]:
    ...     a = yield success(2)
    ...     b = yield success(2)
    ...     return a + b
    >>> f().run(None)
    4

    :param f: the function to decorate
    :return: new function that consumes effects generated by `f`, \
        chaining them together with `and_then`
    """
    @wraps(f)
    def decorator(*args, **kwargs):
        g = f(*args, **kwargs)

        def cont(v):
            try:
                return g.send(v).and_then(cont)
            except StopIteration as e:
                return success(e.value)

        try:
            m = next(g)
            return m.and_then(cont)
        except StopIteration as e:
            return success(e.value)

    return decorator


def sequence_async(iterable: Iterable[Effect[R1, E1, A1]]
                   ) -> Effect[R1, E1, Iterable[A1]]:
    """
    Evaluate each :class:`Effect` in `iterable` asynchronously
    and collect the results

    :example:
    >>> sequence_async([success(v) for v in range(3)]).run(None)
    (0, 1, 2)

    :param iterable: The iterable to collect results from
    :returns: ``Effect`` that produces collected results
    """
    async def run_e(r: RuntimeEnv[R1]):
        awaitables = [e.run_e(r) for e in iterable]  # type: ignore
        trampolines = await asyncio.gather(*awaitables)
        # TODO should this be run in an executor to avoid blocking?
        # maybe depending on the number of effects?
        trampoline = sequence_trampolines(trampolines)
        return trampoline.map(lambda eithers: sequence_eithers(eithers))

    return Effect(run_e)


@curry
def map_m(f: Callable[[A1], Effect[R1, E1, A1]],
          iterable: Iterable[A1]) -> Effect[R1, E1, Iterable[A1]]:
    """
    Map each in element in ``iterable`` to
    an :class:`Effect` by applying ``f``,
    combine the elements by ``and_then``
    from left to right and collect the results

    :example:
    >>> map_m(success, range(3)).run(None)
    (0, 1, 2)

    :param f: Function to map over ``iterable``
    :param iterable: Iterable to map ``f`` over
    :return: ``f`` mapped over ``iterable`` and combined from left to right.
    """
    effects = (f(x) for x in iterable)
    return sequence_async(effects)


@curry
def filter_m(f: Callable[[A], Effect[R1, E1, bool]],
             iterable: Iterable[A]) -> Effect[R1, E1, Iterable[A]]:
    """
    Map each element in ``iterable`` by applying ``f``,
    filter the results by the value returned by ``f``
    and combine from left to right.

    :example:
    >>> filter_m(lambda v: success(v % 2 == 0), range(3)).run(None)
    (0, 2)

    :param f: Function to map ``iterable`` by
    :param iterable: Iterable to map by ``f``
    :return: `iterable` mapped and filtered by `f`
    """
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


def absolve(effect: Effect[Any, NoReturn, Either[E1, A1]]
            ) -> Effect[Any, E1, A1]:
    """
    Move the error type from an :class:`Effect` producing an :class:`Either` \
    into the error channel of the :class:`Effect`

    :example:
    >>> effect = error('Whoops').either().map(
    ...     lambda either: either.get if isinstance(either, Right) else 'Phew!'
    ... )
    >>> absolve(effect).run(None)
    'Phew!'

    :param effect: an :class:`Effect` producing an :class:`Either`
    :return: an :class:`Effect` failing with `E1` or succeeding with `A1`
    """
    async def run_e(r) -> Trampoline[Either[E1, A1]]:
        async def thunk():
            trampoline = await effect.run_e(r)
            return trampoline.and_then(lambda either: Done(either.get))

        return Call(thunk)

    return Effect(run_e)


def error(reason: E1) -> Effect[Any, E1, NoReturn]:
    """
    Create an :class:`Effect` that does nothing but fail with `reason`

    :example:
    >>> error('Whoops!').run(None)
    RuntimeError: 'Whoops!'

    :param reason: Value to fail with
    :return: :class:`Effect` that fails with `reason`
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

    :example:
    >>> combine(success(2), success(2))(lambda a, b: a + b).run(None)
    4

    :param effects: Effects the results of which to pass to the combiner \
        function

    :return: function that takes a combiner function and returns an \
        :class:`Effect` that applies the function to the results of `effects`
    """
    def _(f: Callable[..., A1]):
        effect = sequence_async(effects)
        return effect.map(lambda seq: f(*seq))

    return _


EX = TypeVar('EX', bound=Exception)


# @curry
def catch(*error_type: Type[EX],
          ) -> Callable[[Callable[[], A1]], Effect[Any, EX, A1]]:
    """
    Catch exceptions raised by a function and push them into the error type \
    of an :class:`Effect`

    :example:
    >>> catch(ZeroDivisionError)(lambda: 1 / 0).either().run(None)
    Left(ZeroDivisionError('division by zero'))

    :param error_type: Exception type to catch. All other exceptions will \
        not be handled
    :return: :class:`Effect` that can fail with exceptions raised by the \
        passed function
    """
    def _(f):
        try:
            return success(f())
        except Exception as e:
            if any(isinstance(e, t) for t in error_type):
                return error(e)
            raise e

    return _


def catch_all(f: Callable[[], A1]) -> Effect[Any, Exception, A1]:
    """
    Return an :class:`Effect` that can fail with any exceptions raised by `f`

    :example:
    >>> catch_all(lambda: 1 / 0).either().run(None)
    Left(ZeroDivisionError('division by zero'))

    :param f: All exceptions raised by this functions will be pushed to the \
        error channel of the resulting :class:`Effect`
    :return: :class:`Effect` that cain fail with exceptions raised by `f` \
        or succeed with the result of `f`
    """
    async def run_e(_: Any) -> Trampoline[Either[Exception, A1]]:
        try:
            return Done(Right(f()))
        except Exception as e:
            return Done(Left(e))

    return Effect(run_e)


__all__ = [
    'Effect',
    'success',
    'get_environment',
    'with_effect',
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
