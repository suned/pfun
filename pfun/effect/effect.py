from __future__ import annotations

import asyncio
from functools import wraps
from typing import (Any, Awaitable, Callable, Generator, Generic, Iterable,
                    NoReturn, Type, TypeVar, Union)

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


class Effect(Generic[R, E, A], Immutable):
    """
    Wrapper for functions that are allowed to perform side-effects
    """
    run_e: Callable[[R], Awaitable[Trampoline[Either[E, A]]]]

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
        async def run_e(r: R) -> Trampoline[Either[NoReturn, Either[E, A]]]:
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
        """
        Run the function wrapped by this :class:`Effect`, including potential \
        side-effects. If the function fails the resulting error will be \
        raised as an exception.

        :param r: The environment with which to run this :class:`Effect`
        :param asyncio_run: Function to run the coroutine returned by the \
            wrapped function
        :returns: The succesful result of the wrapped functions if it succeeds
        """
        async def _run() -> A:
            trampoline = await self.run_e(r)  # type: ignore
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
        Map `f` over the produced by this :class:`Effect` once it is run

        :example:
        >>> success(2).map(lambda v: v + 2).run(None)
        4

        :param f: function to map over this :class:`Effect`
        :return: new :class:`Effect` with `f` applied to the \
            value produced by this :class:`Effect`.
        """
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
    async def run_e(r):
        return Done(Right(r))

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
    async def run_e(r):
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
def catch(error_type: Type[EX],
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
        except error_type as e:
            return error(e)

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
