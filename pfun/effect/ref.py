from typing import Generic, TypeVar, Any, Callable, NoReturn
from asyncio import Lock

from . import Effect
from ..immutable import Immutable
from ..either import Either, Left, Right
from ..aio_trampoline import Done, Trampoline

A = TypeVar('A')
E = TypeVar('E')


class Ref(Immutable, Generic[A]):
    value: A
    lock: Lock = Lock()

    def get(self) -> Effect[Any, NoReturn, A]:
        async def run_e(_) -> Trampoline[Either[NoReturn, A]]:
            async with self.lock:
                return Done(Right(self.value))

        return Effect(run_e)

    def __repr__(self):
        return f'Ref({repr(self.value)})'

    def put(self, value: A) -> Effect[Any, NoReturn, None]:
        async def run_e(_) -> Trampoline[Either[NoReturn, None]]:
            async with self.lock:
                # purists avert your eyes
                object.__setattr__(self, 'value', value)
            return Done(Right(None))

        return Effect(run_e)

    def modify(self, f: Callable[[A], A]) -> Effect[Any, NoReturn, None]:
        async def run_e(_) -> Trampoline[Either[NoReturn, None]]:
            async with self.lock:
                new = f(self.value)
                object.__setattr__(self, 'value', new)
            return Done(Right(None))

        return Effect(run_e)

    def try_modify(self,
                   f: Callable[[A], Either[E, A]]) -> Effect[Any, E, None]:
        async def run_e(_) -> Trampoline[Either[E, None]]:
            async with self.lock:
                either = f(self.value)
                if isinstance(either, Left):
                    return Done(either)
                else:
                    object.__setattr__(self, 'value', either.get)
                return Done(Right(None))

        return Effect(run_e)
