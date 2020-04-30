from __future__ import annotations
from typing import (
    TypeVar,
    Generic,
    Callable,
    Any,
    Generator,
    Awaitable,
    Union,
    NoReturn,
    Type,
    Iterable
)
import asyncio
from functools import wraps
from typing_extensions import final

from ..immutable import Immutable
from ..either import Either, Right, Left, sequence as sequence_eithers, filter_m as filter_eithers
from ..aio_trampoline import Done, Call, Trampoline, sequence as sequence_trampolines
from ..curry import curry

R = TypeVar('R', contravariant=True)
E = TypeVar('E', covariant=True)
E2 = TypeVar('E2')
A = TypeVar('A', covariant=True)
B = TypeVar('B')


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

    def either(self) -> Effect[R, NoReturn, Either[E, A]]:
        async def run_e(r: R) -> Trampoline[Either[NoReturn, Either[E, A]]]:
            trampoline = await self.run_e(r)  # type: ignore
            return trampoline.and_then(lambda either: Done(Right(either)))

        return Effect(run_e)

    def recover(self,
                f: Callable[[E], Effect[Any, E2, A]]) -> Effect[Any, E2, A]:
        async def run_e(r: R) -> Trampoline[Either[E2, B]]:
            async def k(either: Either) -> Trampoline[Either[E2, A]]:
                if isinstance(either, Left):
                    return await f(either.get).run_e(r)  # type: ignore
                return Done(either)

            trampoline = await self.run_e(r)  # type: ignore
            return trampoline.and_then(k)

        return Effect(run_e)

    def run(self, r: R, asyncio_run=asyncio.run) -> A:
        async def _run() -> A:
            trampoline = await self.run_e(r)  # type: ignore
            result = await trampoline.run()
            if isinstance(result, Left):
                error = result.get
                if isinstance(error, Exception):
                    raise error
                else:
                    raise Exception(f'Run error: {error}')
            else:
                return result.get

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


def wrap(value: A1) -> Effect[Any, NoReturn, A1]:
    async def run_e(_):
        return Done(Right(value))

    return Effect(run_e)


def get_environment() -> Effect[Any, NoReturn, Any]:
    async def run_e(r):
        return Done(Right(r))

    return Effect(run_e)


def from_awaitable(awaitable: Awaitable[A1]) -> Effect[Any, NoReturn, A1]:
    async def run_e(_):
        return Done(Right(await awaitable))

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


def sequence_async(iterable: Iterable[Effect[R1, E1, A1]]
                   ) -> Effect[R1, E1, Iterable[A1]]:
    async def run_e(r):
        awaitables = [e.run_e(r) for e in iterable]
        trampolines = await asyncio.gather(*awaitables)
        # TODO should this be run in an executor to avoid blocking?
        # maybe depending on the number of effects?
        trampoline = sequence_trampolines(trampolines)
        return trampoline.map(lambda eithers: sequence_eithers(eithers))

    return Effect(run_e)


@curry
def map_m(f: Callable[[A1], Effect[R1, E1, A1]],
          iterable: Iterable[A1]) -> Effect[R1, E1, Iterable[A1]]:
    effects = (f(x) for x in iterable)
    return sequence_async(effects)


@curry
def filter_m(f: Callable[[A], Effect[R1, E1, bool]],
             iterable: Iterable[A]) -> Effect[R1, E1, Iterable[A]]:
    async def run_e(r):
        awaitables = [f(a).run_e(r) for a in iterable]
        trampolines = await asyncio.gather(*awaitables)
        trampoline = sequence_trampolines(trampolines)
        return trampoline.map(
            lambda eithers: sequence_eithers(eithers).
            map(lambda bs: tuple(a for a, b in zip(iterable, bs) if b))
        )

    return Effect(run_e)


def absolve(effect: Effect[Any, NoReturn, Either[E1, A1]]
            ) -> Effect[Any, E1, A1]:
    async def run_e(r) -> Trampoline[Either[E1, A1]]:
        trampoline = await effect.run_e(r)  # type: ignore
        return trampoline.and_then(lambda either: Done(either.get))

    return Effect(run_e)


def fail(error: E1) -> Effect[Any, E1, NoReturn]:
    async def run_e(r):
        return Done(Left(error))

    return Effect(run_e)


A2 = TypeVar('A2')


def combine(*effects: Effect[R1, E1, A2]
            ) -> Callable[[Callable[..., A1]], Effect[Any, Any, A1]]:
    def _(f: Callable[..., A1]):
        effect = sequence_async(effects)
        return effect.map(lambda seq: f(*seq))

    return _


EX = TypeVar('EX', bound=Exception)


# @curry
def catch(error_type: Type[EX],
          ) -> Callable[[Callable[[], A1]], Effect[Any, EX, A1]]:
    def _(f):
        try:
            return wrap(f())
        except error_type as e:
            return fail(e)

    return _


def catch_all(f: Callable[[], A1]) -> Effect[Any, Exception, A1]:
    async def run_e(_: Any) -> Trampoline[Either[Exception, A1]]:
        try:
            return Done(Right(f()))
        except Exception as e:
            return Done(Left(e))

    return Effect(run_e)


__all__ = [
    'Effect',
    'wrap',
    'get_environment',
    'with_effect',
    'sequence_async',
    'filter_m',
    'map_m',
    'absolve',
    'fail',
    'combine',
    'catch',
    'catch_all',
    'from_awaitable'
]
