from __future__ import annotations
from typing import (
    TypeVar,
    Generic,
    Callable,
    Any,
    Generator,
    Awaitable,
    Union,
    TYPE_CHECKING
)
import asyncio
from functools import wraps
from typing_extensions import final

from ..immutable import Immutable
from ..either import Either, Right, Left, sequence as sequence_eithers
from ..aio_trampoline import Done, Call, Trampoline

R = TypeVar('R', contravariant=True)
E = TypeVar('E', covariant=True)
E2 = TypeVar('E2')
A = TypeVar('A', covariant=True)
B = TypeVar('B')

if TYPE_CHECKING:

    @final
    class Never(Any):
        def __init__(self):
            raise TypeError('Cannot instantiate "Never" type')
else:

    @final
    class Never:
        def __init__(self):
            raise TypeError('Cannot instantiate "Never" type')


class Effect(Generic[R, E, A], Immutable):
    run_e: Callable[[R], Awaitable[Trampoline[Either[E, A]]]]

    def and_then(
        self,
        f: Callable[[A],
                    Union[Awaitable[Effect[Any, E2, B]], Effect[Any, E2, B]]]
    ) -> Effect[Any, Union[E, E2], B]:
        async def run_e(r: R) -> Trampoline[Either[Union[E, E2], B]]:
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

    def either(self) -> Effect[R, Never, Either[E, A]]:
        async def run_e(r: R) -> Trampoline[Either[Never, Either[E, A]]]:
            trampoline = await self.run_e(r)  # type: ignore
            return trampoline.and_then(lambda either: Done(Right(either)))

        return Effect(run_e)

    def run(self, r: R, asyncio_run=asyncio.run) -> Either[E, A]:
        async def _run():
            trampoline = await self.run_e(r)
            return await trampoline.run()

        return asyncio_run(_run())

    def map(self, f: Callable[[A], Union[Awaitable[B], B]]) -> Effect[R, E, B]:
        async def run_e(r: R) -> Trampoline[Either[E, B]]:
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


def wrap(value: A1) -> Effect[Any, Never, A1]:
    async def run_e(_):
        return Done(Right(value))

    return Effect(run_e)


def get_environment() -> Effect[Any, Never, Any]:
    async def run_e(r):
        return Done(Right(r))

    return Effect(run_e)


def from_awaitable(awaitable: Awaitable[A1]) -> Effect[Any, Never, A1]:
    async def run_e(_):
        return Right(await awaitable)

    return Effect(run_e)


B1 = TypeVar('B1')
Effects = Generator[Effect[R1, E1, Any], Any, B1]


def with_effect(f: Callable[..., Effects[R1, E1, A1]]
                ) -> Callable[..., Effect[R1, E1, A1]]:
    @wraps(f)
    def decorator(*args, **kwargs):
        g = f(*args, **kwargs)

        def cont(v):
            try:
                return g.send(v).and_then(cont)
            except StopIteration as e:
                return wrap(e.value)

        try:
            m = next(g)
            return m.and_then(cont)
        except StopIteration as e:
            return wrap(e.value)

    return decorator


def sequence_async(iterable):
    async def run_e(r):
        awaitables = [e.run_e(r) for e in iterable]
        trampolines = await asyncio.gather(*awaitables)
        # TODO should this be run in an executor to avoid blocking?
        # maybe depending on the number of effects?
        trampoline = sequence_trampolines(trampolines)
        return trampoline.map(lambda eithers: sequence_eithers(eithers))

    return Effect(run_e)


def map_m(f, iterable):
    effects = (f(x) for x in iterable)
    return sequence(effects)


def absolve(effect: Effect[Any, Never, Either[E1, A1]]) -> Effect[Any, E1, A1]:
    async def run_e(r) -> Trampoline[Either[E1, A1]]:
        trampoline = await effect.run_e(r)  # type: ignore
        return trampoline.and_then(lambda either: Done(either.get))

    return Effect(run_e)


def fail(error: E1) -> Effect[Any, E1, Any]:
    async def run_e(r):
        return Done(Left(error))

    return Effect(run_e)


def combine(*effects: Effect
            ) -> Callable[[Callable[..., A1]], Effect[Any, Any, A1]]:
    def _(f: Callable[..., A1]):
        effect = sequence_async(effects)
        return effect.map(lambda seq: f(*seq))

    return _


def lift(f: Callable[..., A1]) -> Callable[..., Effect[Any, Any, A1]]:
    def _(*effects: Effect) -> Effect[Any, Any, A1]:
        effect = sequence_async(effects)
        return effect.map(lambda seq: f(*seq))

    return _
