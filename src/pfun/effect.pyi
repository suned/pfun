from typing import (Any, AsyncContextManager, Awaitable, Callable, Generic,
                    Iterable, NoReturn, Optional, Tuple, Type, TypeVar, Union,
                    overload)
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import AsyncExitStack
import asyncio

from pfun.functions import curry
from pfun.immutable import Immutable
from pfun.either import Either, Left, Right
from pfun.monad import Monad


R = TypeVar('R', contravariant=True)
E = TypeVar('E', covariant=True)
E2 = TypeVar('E2')
A = TypeVar('A', covariant=True)
B = TypeVar('B')

C = TypeVar('C', bound=AsyncContextManager)

F = TypeVar('F', bound=Callable[..., 'Effect'])


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
    def __init__(self, 
                 resource_factory: Callable[[], Union[Either[E, C], Awaitable[Either[E, C]]]]):
        ...

    def get(self) -> Effect[object, E, C]: ...


class RuntimeEnv(Immutable, Generic[A]):
    """
    Wraps the user supplied dependency R and supplies various utilities
    for the effect runtime such as the resource AsyncExitStack

    :attribute r: The user supplied dependency value
    :attribute exit_stack: AsyncExitStack used to enable Effect resources
    """
    r: A
    exit_stack: AsyncExitStack
    process_executor: ProcessPoolExecutor
    thread_executor: ThreadPoolExecutor

    async def run_in_process_executor(
        self, f: Callable[..., B], *args: Any, **kwargs: Any
    ) -> B: ...

    async def run_in_thread_executor(
        self, f: Callable[..., B], *args: Any, **kwargs: Any
    ) -> B: ...


class Effect(Generic[R, E, A], Immutable, Monad):
    """
    Wrapper for functions of type \
    `Callable[[R], Awaitable[pfun.Either[E, A]]]` that are allowed to \
    perform side-effects
    """

    def and_then(
        self,
        f: Callable[[A],
                    Union[Awaitable[Effect[Any, E2, B]], Effect[Any, E2, B]]]
    ) -> Effect[Any, Union[E, E2], B]: ...

    def discard_and_then(self, effect: Effect[Any, E2, B]
                         ) -> Effect[Any, Union[E, E2], B]: ...

    def memoize(self) -> Effect[R, E, A]: ...

    def recover(self, f: Callable[[E], Effect[Any, E2, B]]
                ) -> Effect[Any, E2, Union[A, B]]:
        ...

    def ensure(self, effect: Effect[Any, NoReturn, Any]) -> Effect[Any, E, A]: ...

    def either(self) -> Effect[R, NoReturn, Either[E, A]]: ...

    def with_repr(self, repr_: str) -> Effect[R, E, A]: ...

    async def __call__(
        self, r: R, max_processes: int = None, max_threads: int = None
    ) -> A: ...
    
    def run(
        self,
        r: R,
        max_processes: int = None,
        max_threads: int = None
    ) -> A: ...

    @add_method_repr
    def map(self, f: Callable[[A], Union[Awaitable[B], B]]) -> Effect[R, E, B]: ...


R1 = TypeVar('R1')
E1 = TypeVar('E1')
A1 = TypeVar('A1')


def success(value: A1) -> Effect[object, NoReturn, A1]: ...


@overload
def depend(r_type: None = None) -> Depends: ...


@overload
def depend(r_type: Type[R1] = None) -> Depends[R1, R1]: ...


def from_awaitable(awaitable: Awaitable[A1]) -> Effect[object, NoReturn, A1]:
    ...


def sequence_async(iterable: Iterable[Effect[R1, E1, A1]]
                   ) -> Effect[R1, E1, Iterable[A1]]:
    ...


def sequence(iterable: Iterable[Effect[R1, E1, A1]]
             ) -> Effect[R1, E1, Iterable[A1]]:
    ...


@curry
def for_each(f: Callable[[A1], Effect[R1, E1, B]],
             iterable: Iterable[A1]) -> Effect[R1, E1, Iterable[B]]:
    ...


@curry
def filter_(f: Callable[[A], Effect[R1, E1, bool]],
            iterable: Iterable[A]) -> Effect[R1, E1, Iterable[A]]:
    ...


def absolve(effect: Effect[R1, NoReturn, Either[E1, A1]]
            ) -> Effect[R1, E1, A1]:
    ...


def error(reason: E1) -> Effect[object, E1, NoReturn]:
    ...

A2 = TypeVar('A2')


def combine(
    *effects: Effect[R1, E1, A2]
) -> Callable[[Callable[..., Union[Awaitable[A1], A1]]], Effect[Any, Any, A1]]:
    ...

def combine_cpu_bound(
    *effects: Effect[R1, E1, A2]
) -> Callable[[Callable[..., A1]], Effect[Any, Any, A1]]:
    ...

def combine_io_bound(
    *effects: Effect[R1, E1, A2]
) -> Callable[[Callable[..., A1]], Effect[Any, Any, A1]]:
    ...


L = TypeVar('L', covariant=True, bound=Callable)


class lift(Generic[L]):
    def __init__(self, f: L):
        ...

    def __call__(self, *effects: Effect) -> Effect:
        ...


class lift_cpu_bound(Generic[L]):
    def __init__(self, f: L):
        ...

    def __call__(self, *effects: Effect) -> Effect:
        ...


class lift_io_bound(Generic[L]):
    def __init__(self, f: L):
        ...

    def __call__(self, *effects: Effect) -> Effect:
        ...


def from_callable(
    f: Callable[[R1], Union[Awaitable[Either[E1, A1]], Either[E1, A1]]]
) -> Effect[R1, E1, A1]:
    ...

def from_io_bound_callable(
    f: Callable[[R1], Either[E1, A1]]
) -> Effect[R1, E1, A1]:
    ...


def from_cpu_bound_callable(
    f: Callable[[R1], Either[E1, A1]]
) -> Effect[R1, E1, A1]:
    ...


EX = TypeVar('EX', bound=Exception)
F1 = TypeVar('F1', bound=Callable)


class catch(Immutable, Generic[EX], init=False):
    def __init__(self, error: Type[EX], *errors: Type[EX]):
        ...

    @overload
    def __call__(self, f: Callable[..., Awaitable[B]]
                 ) -> Callable[..., Try[EX, B]]:
        ...

    @overload
    def __call__(self, f: Callable[..., B]
                 ) -> Callable[..., Try[EX, B]]:
        ...


class catch_io_bound(Immutable, Generic[EX], init=False):
    def __init__(self, error: Type[EX], *errors: Type[EX]):
        ...

    def __call__(self, f: Callable[..., B]
                 ) -> Callable[..., Try[EX, B]]:
        ...


class catch_cpu_bound(Immutable, Generic[EX], init=False):
    def __init__(self, error: Type[EX], *errors: Type[EX]):
        ...

    def __call__(self, f: Callable[..., B]
                 ) -> Callable[..., Try[EX, B]]:
        ...


def add_method_repr(f: F1) -> F1: ...
def add_repr(f: F1) -> F1: ...


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
