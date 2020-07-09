from asyncio import Lock
from typing import Any, Callable, Generic, NoReturn, Optional, TypeVar, cast

from ..aio_trampoline import Done, Trampoline
from ..either import Either, Left, Right
from ..immutable import Immutable
from .effect import Effect

A = TypeVar('A')
E = TypeVar('E')


class Ref(Immutable, Generic[A], init=False):
    """
    Wraps a value that can be mutated as an :class:`Effect`

    :attribute value: the wrapped value
    """
    _lock: Optional[Lock]
    value: A

    def __init__(self, value: A):
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

    def get(self) -> Effect[Any, NoReturn, A]:
        """
        Get an :class:`Effect` that reads the current state of the value

        :example:
        >>> ref = Ref('the state')
        >>> ref.get().run(None)
        'the state'

        :return: :class:`Effect` that reads the current state
        """
        async def run_e(_) -> Trampoline[Either[NoReturn, A]]:
            async with self.__lock:
                return Done(Right(self.value))

        return Effect(run_e)

    def __repr__(self):
        return f'Ref({repr(self.value)})'

    def put(self, value: A) -> Effect[Any, NoReturn, None]:
        """
        Get an :class:`Effect` that updates the current state of the value

        :example:
        >>> ref = Ref('initial state')
        >>> ref.put('new state').run(None)
        None
        >>> ref.value
        'new state'

        :param value: new state
        :return: :class:`Effect` that updates the state
        """
        async def run_e(_) -> Trampoline[Either[NoReturn, None]]:
            async with self.__lock:
                # purists avert your eyes
                object.__setattr__(self, 'value', value)
            return Done(Right(None))

        return Effect(run_e)

    def modify(self, f: Callable[[A], A]) -> Effect[Any, NoReturn, None]:
        """
        Modify the value wrapped by this :class:`Ref` by \
            applying `f` in isolation

        :example:
        >>> ref = Ref([])
        >>> ref.modify(lambda l: l + [1]).run(None)
        None
        >>> ref.value
        [1]

        :param f: function that accepts the current state and returns \
            a new state
        :return: :class:`Effect` that updates the state to the result of `f`
        """
        async def run_e(_) -> Trampoline[Either[NoReturn, None]]:
            async with self.__lock:
                new = f(self.value)
                object.__setattr__(self, 'value', new)
            return Done(Right(None))

        return Effect(run_e)

    def try_modify(self,
                   f: Callable[[A], Either[E, A]]) -> Effect[Any, E, None]:
        """
        Try to update the current state with the result of `f` if it succeeds.
        The state is updated if `f` returns a :class:`Right` value, and kept
        as is otherwise

        :example:
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

        :param f: function that accepts the current state and \
            returns a :class:`Right` wrapping a new state \
            or a :class:`Left` value wrapping an error
        :return: an :class:`Effect` that updates the state if `f` succeeds
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
