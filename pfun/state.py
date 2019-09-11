from typing import Generic, TypeVar, Callable, Tuple, Iterable

from .immutable import Immutable
from .util import sequence_, map_m_, filter_m_
from .curry import curry

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')


class State(Generic[B, A], Immutable):
    """
    Class representing a computation that is not yet complete,
    but will complete when given a state of type A
    """
    f: Callable[[A], Tuple[B, A]]

    def and_then(self, f: 'Callable[[B], State[C, A]]') -> 'State[C, A]':
        """
        Chain together state computations,
        keeping track of state without mutable state

        :example:
        >>> get().and_then(
        ...     lambda s: put(s + ['final state'])
        ... ).run(['initial state'])
        (), ['initial state', 'final state']


        :param f: Function to pass the result of this :class:`State` instance \
        once it can be computed
        :return: new :class:`State` which wraps the result of \
        passing the result of this :class:`State` instance to ``f``
        """
        def _(b: B, a: A) -> Tuple[C, A]:
            return f(b).f(a)  # type: ignore

        return State(lambda a: _(*self.f(a)))  # type: ignore

    def run(self, a: A) -> Tuple[B, A]:
        """
        Get the result of this :class:`State` by passing the state ``a``
        to the wrapped function

        :example:
        >>> append_to_state = lambda state: value(state + ['final state'])
        >>> get().and_then(append_to_state).run(['initial state'])
        ['initial state', 'final state'], ['initial state', 'final state']

        :param a: State to run this :class:`State` instance on
        :return: Result of running :class:`State` instance with ``a`` as state
        """
        return self.f(a)  # type: ignore

    __call__ = run

    def map(self, f: Callable[[B], C]) -> 'State[C, A]':
        def _(b: B, a: A):
            return f(b), a

        return State(lambda a: _(*self(a)))  # type: ignore


def put(a: A) -> State[None, A]:
    """
    Update the state in the current computation

    :example:
    >>> put('state').run('')
    (), 'state'

    :param a: The new state
    :return: :class:`State` with ``a`` as the new state
    """
    return State(lambda state: (None, a))  # type: ignore


def get() -> State[A, A]:
    """
    Get the current state

    :example:
    >>> get().run('state')
    'state', 'state'

    :return: :class:`State` with the current state as its result
    """
    return State(lambda b: (b, b))  # type: ignore


def value(b: B) -> State[B, A]:
    """
    Put a value in the :class:`State` context

    :example:
    >>> value(1).run('state')
    1, 'state'

    :param b: the value to put in a :class:`State` context
    :return: :class:`State` that will produce ``b`` no matter the state
    """
    return State(lambda a: (b, a))  # type: ignore


@curry
def map_m(f: Callable[[A], State[A, B]],
          iterable: Iterable[A]) -> State[Iterable[A], B]:
    return map_m_(value, f, iterable)
