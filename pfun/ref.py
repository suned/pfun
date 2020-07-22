from asyncio import Lock
from typing import Callable, Generic, NoReturn, Optional, TypeVar, cast

from .aio_trampoline import Done, Trampoline
from .effect import Effect, Success, Try, add_method_repr
from .either import Either, Left, Right
from .immutable import Immutable

A = TypeVar('A')
E = TypeVar('E')


class Ref(Immutable, Generic[A], init=False):
    """
    Wraps a value that can be mutated as an `Effect`
    """
    _lock: Optional[Lock]
    value: A

    def __init__(self, value: A):
        """
        Args:
            value: The initial state
        """
        object.__setattr__(self, 'value', value)
        object.__setattr__(self, '_lock', None)

    @property
    def __lock(self) -> Lock:
        # All this nonsense is to ensure that locks are not initialised
        # before the thread running the event loop is initialised.
        # If the lock is initialised in the main thread,
        # it may lead to
        # RuntimeError: There is no current event loop in thread 'MainThread'.
        # see https://tinyurl.com/yc9kd77s
        if self._lock is None:
            object.__setattr__(self, '_lock', Lock())
        return cast(Lock, self._lock)

    @add_method_repr
    def get(self) -> Success[A]:
        """
        Get an `Effect` that reads the current state of the value

        Example:
            >>> ref = Ref('the state')
            >>> ref.get().run(None)
            'the state'

        Return:
            `Effect` that reads the current state
        """
        async def run_e(_) -> Trampoline[Either[NoReturn, A]]:
            async with self.__lock:
                return Done(Right(self.value))

        return Effect(run_e, f'pfun.ref.{repr(self)}.get()')

    def __repr__(self):
        return f'Ref({repr(self.value)})'

    @add_method_repr
    def put(self, value: A) -> Success[None]:
        """
        Get an `Effect` that updates the current state of the value

        Example:
            >>> ref = Ref('initial state')
            >>> ref.put('new state').run(None)
            None
            >>> ref.value
            'new state'

        Args:
            value: new state

        Return:
            `Effect` that updates the state
        """
        async def run_e(_) -> Trampoline[Either[NoReturn, None]]:
            async with self.__lock:
                # purists avert your eyes
                object.__setattr__(self, 'value', value)
            return Done(Right(None))

        return Effect(run_e)

    @add_method_repr
    def modify(self, f: Callable[[A], A]) -> Success[None]:
        """
        Modify the value wrapped by this `Ref` by \
            applying `f` in isolation

        Example:
            >>> ref = Ref([])
            >>> ref.modify(lambda l: l + [1]).run(None)
            None
            >>> ref.value
            [1]

        Args:
            f: function that accepts the current state and returns \
            a new state
        Return:
            `Effect` that updates the state to the result of `f`
        """
        async def run_e(_) -> Trampoline[Either[NoReturn, None]]:
            async with self.__lock:
                new = f(self.value)
                object.__setattr__(self, 'value', new)
            return Done(Right(None))

        return Effect(run_e)

    @add_method_repr
    def try_modify(self,
                   f: Callable[[A], Either[E, A]]) -> Try[E, None]:
        """
        Try to update the current state with the result of `f` if it succeeds.
        The state is updated if `f` returns a `Right` value, and kept
        as is otherwise

        Example:
            >>> from pfun.either import Left, Right
            >>> ref = Ref('initial state')
            >>> ref.try_modify(lambda _: Left('Whoops!')).either().run(None)
            Left('Whoops!')
            >>> ref.value
            'initial state'
            >>> ref.try_modify(lambda _: Right('new state')).run(None)
            None
            >>> ref.value
            'new state'

        Args:
            f: function that accepts the current state and \
            returns a `Right` wrapping a new state \
            or a `Left` value wrapping an error

        Return:
            an `Effect` that updates the state if `f` succeeds
        """
        async def run_e(_) -> Trampoline[Either[E, None]]:
            async with self.__lock:
                either = f(self.value)
                if isinstance(either, Left):
                    return Done(either)
                else:
                    object.__setattr__(self, 'value', either.get)
                return Done(Right(None))

        return Effect(run_e)
