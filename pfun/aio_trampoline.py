from abc import ABC, abstractmethod
from asyncio import iscoroutine
from typing import Awaitable, Callable, Generic, Iterable, TypeVar, Union, cast

from .immutable import Immutable
from .monad import Monad, sequence_

A = TypeVar('A', covariant=True)
B = TypeVar('B')
C = TypeVar('C')


class Trampoline(Immutable, Monad, Generic[A], ABC):
    """
    Base class for Trampolines. Useful for writing stack safe-safe
    recursive functions.
    """
    @abstractmethod
    async def _resume(self) -> 'Trampoline[A]':
        pass

    @abstractmethod
    async def _handle_cont(
        self, cont: Callable[[A], 'Trampoline[B]']
    ) -> 'Trampoline[B]':
        pass

    @property
    def _is_done(self) -> bool:
        return isinstance(self, Done)

    def and_then(self, f: Callable[[A], 'Trampoline[B]']) -> 'Trampoline[B]':
        """
        Apply ``f`` to the value wrapped by this trampoline.

        :param f: function to apply the value in this trampoline
        :return: Result of applying ``f`` to the value wrapped by \
            this trampoline
        """
        return AndThen(self, f)

    def map(self, f: Callable[[A], B]) -> 'Trampoline[B]':
        """
        Map ``f`` over the value wrapped by this trampoline.

        :param f: function to wrap over this trampoline
        :return: new trampoline wrapping the result of ``f``
        """
        return self.and_then(lambda a: Done(f(a)))  # type: ignore

    async def run(self) -> A:
        """
        Interpret a structure of trampolines to produce a result

        :return: result of intepreting this structure of \
            trampolines
        """
        trampoline = self
        while not trampoline._is_done:
            trampoline = await trampoline._resume()

        return cast(Done[A], trampoline).a


class Done(Trampoline[A]):
    """
    Represents the result of a recursive computation.
    """
    a: A

    async def _resume(self) -> Trampoline[A]:
        return self

    async def _handle_cont(
        self,
        cont: Callable[[A], Union[Awaitable[Trampoline[B]], Trampoline[B]]]
    ) -> Trampoline[B]:
        result = cont(self.a)
        if iscoroutine(result):
            return await result  # type: ignore
        return result  # type: ignore


class Call(Trampoline[A]):
    """
    Represents a recursive call.
    """
    thunk: Callable[[], Awaitable[Trampoline[A]]]

    async def _handle_cont(self, cont: Callable[[A], Trampoline[B]]
                           ) -> Trampoline[B]:
        trampoline = await self.thunk()  # type: ignore
        return trampoline.and_then(cont)

    async def _resume(self) -> Trampoline[A]:
        return await self.thunk()  # type: ignore


class AndThen(Generic[A, B], Trampoline[B]):
    """
    Represents monadic bind for trampolines as a class to avoid
    deep recursive calls to ``Trampoline.run`` during interpretation.
    """
    sub: Trampoline[A]
    cont: Callable[[A], Union[Trampoline[B], Awaitable[Trampoline[B]]]]

    async def _handle_cont(self, cont: Callable[[B], Trampoline[C]]
                           ) -> Trampoline[C]:
        return self.sub.and_then(self.cont).and_then(cont)  # type: ignore

    async def _resume(self) -> Trampoline[B]:
        return await self.sub._handle_cont(self.cont)  # type: ignore

    def and_then(  # type: ignore
        self, f: Callable[[A], Trampoline[B]]
    ) -> Trampoline[B]:
        def cont(x):
            async def thunk():
                t = self.cont(x)
                if iscoroutine(t):
                    print('awaiting')
                    t = await t
                return t.and_then(f)

            return Call(thunk)

        return AndThen(self.sub, cont)


def sequence(iterable: Iterable[Trampoline[A]]) -> Trampoline[Iterable[A]]:
    """
    Evaluate each :class:`Trampoline` in `iterable` from left to right
    and collect the results

    :example:
    >>> sequence([Just(v) for v in range(3)])
    Just((0, 1, 2))

    :param iterable: The iterable to collect results from
    :returns: ``Trampoline`` of collected results
    """
    return cast(Trampoline[Iterable[A]], sequence_(Done, iterable))


__all__ = ['Trampoline', 'Done', 'sequence', 'Call', 'AndThen']
