from typing import Generic, TypeVar, Any, Callable
from asyncio import Lock

from . import Effect, Never
from ..immutable import Immutable
from ..either import Either, Left, Right

A = TypeVar('A')


class Ref(Immutable, Generic[A]):
    value: A
    lock: Lock = Lock()

    def get(self) -> Effect[Any, Never, A]:
        async def run_e(_) -> Either[Never, A]:
            async with self.lock:
                return Right(self.value)

        return Effect(run_e)

    def __repr__(self):
        return f'Ref({repr(self.value)})'

    def put(self, value: A) -> Effect[Any, Never, None]:
        async def run_e(_) -> Either[Never, None]:
            async with self.lock:
                # purists avert your eyes
                object.__setattr__(self, 'value', value)
            return Right(None)

        return Effect(run_e)

    def modify(self, f: Callable[[A], A]) -> Effect[Any, Never, None]:
        async def run_e(_) -> Either[Never, None]:
            async with self.lock:
                new = f(self.value)
                object.__setattr__(self, 'value', new)
            return Right(None)

        return Effect(run_e)
