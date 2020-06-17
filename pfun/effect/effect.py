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
    """
    Wrapper for functions that perform side-effects
    """
    run_e: Callable[[R], Awaitable[Trampoline[Either[E, A]]]]

    def and_then(
        self,
        f: Callable[[A],
                    Union[Awaitable[Effect[Any, E2, B]], Effect[Any, E2, B]]]
    ) -> Effect[Any, Union[E, E2], B]:
        """
        Create new :class:`Effect` that applies ``f`` to the result of running this effect successfully.
        If this :class:`Effect` fails, ``f`` is not applied.

        :example:
        >>> success(2).and_then(lambda i: success(i + 2)).run(None)
        4
        
        :param f: Function to pass the result of this :class:`Effect` instance \
        once it can be computed
        :return: New :class:`Effect` which wraps the result of \
        passing the result of this :class:`Effect` instance to ``f``
        """
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
    
    def discard_and_then(self, effect: Effect[Any, E2, B]) -> Effect[Any, Union[E, E2], B]:
        """
        Create a new effect that discards the result of this effect, and produces instead ``effect``. Like ``and_then`` but does not require
        you to handle the result. Convenient for effects that produce ``None``, like writing to files.
        :example:
        >>> class Env:
                files = effect.files.Files()
        >>> effect.files.write('foo.txt', 'Hello!').discard_and_then(effect.files.read('foo.txt')).run(Env())
        Hello!

        :param: :class:`Effect` instance to run after this :class:`Effect` has run successfully.
        """
        return self.and_then(lambda _: effect)  # type: ignore

    def either(self) -> Effect[R, NoReturn, Either[E, A]]:
        """
        Push the potential error into the success channel as an either, allowing
        error handling.
        :example:
        >>> failure('Whoops!').either().map(lambda either: either.get if isinstance(either, Right) else 'Phew!').run(None)
        'Phew!'

        :return: New :class:`Effect` that produces a :class:`Left[E]` if it has failed, or a \
            :class:`Right[A]` if it succeeds 
        """
        async def run_e(r: R) -> Trampoline[Either[NoReturn, Either[E, A]]]:
            async def thunk() -> Trampoline[Either[NoReturn, Either[E, A]]]:
                trampoline = await self.run_e(r)  # type: ignore
                return trampoline.and_then(lambda either: Done(Right(either)))
            
            return Call(thunk)

        return Effect(run_e)

    def recover(self,
                f: Callable[[E], Effect[Any, E2, A]]) -> Effect[Any, E2, A]:
        """
        Create new :class:`Effect` that applies ``f`` to the result of running this effect successfully.
        If this :class:`Effect` fails, ``f`` is not applied.

        :example:
        >>> success(2).and_then(lambda i: success(i + 2)).run(None)
        4
        
        :param f: Function to pass the result of this :class:`Effect` instance \
        once it can be computed
        :return: New :class:`Effect` which wraps the result of \
        passing the result of this :class:`Effect` instance to ``f``
        """
        async def run_e(r: R) -> Trampoline[Either[E2, A]]:
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


def success(value: A1) -> Effect[Any, NoReturn, A1]:
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
                return success(e.value)

        try:
            m = next(g)
            return m.and_then(cont)
        except StopIteration as e:
            return success(e.value)

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


def failure(reason: E1) -> Effect[Any, E1, NoReturn]:
    async def run_e(r):
        return Done(Left(reason))

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
            return success(f())
        except error_type as e:
            return failure(e)

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
    'success',
    'get_environment',
    'with_effect',
    'sequence_async',
    'filter_m',
    'map_m',
    'absolve',
    'failure',
    'combine',
    'catch',
    'catch_all',
    'from_awaitable'
]
