from typing import Generic, TypeVar, Callable, Tuple

from .immutable import Immutable

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')


class State(Generic[B, A], Immutable):
    """
    Class representing a computation that is not yet complete, but will complete
    when given a state of type A
    """
    def __init__(self, f: Callable[[A], Tuple[B, A]]):
        """
        Initialize a :class:`State` that will produce a value of type B when
        given a state of type A

        :param f: Function representing the unfinished computation
        """
        self.f = f

    def and_then(self, f: 'Callable[[B], State[C, A]]') -> 'State[C, A]':
        """
        Chain together state computations, keeping track of state without mutable state

        :example:
        >>> get().and_then(
        ...     lambda s: put(s + ['final state'])
        ... ).run(['initial state'])
        (), ['initial state', 'final state']


        :param f: Function to pass the result of this :class:`State` instance \
        once it can be computed
        :return: new :class:`State` which wraps the result of passing the result \
        of this :class:`State` instance to ``f``
        """
        def _(b: B, a: A) -> Tuple[C, A]:
            return f(b).f(a)
        return State(lambda a: _(*self.f(a)))

    def run(self, a: A) -> Tuple[B, A]:
        """
        Get the result of this :class:`State` by passing the state ``a``
        to the wrapped function

        :example:
        >>> get().and_then(lambda state: value(state + ['final state'])).run(['initial state'])
        ['initial state', 'final state'], ['initial state', 'final state']

        :param a: State to run this :class:`State` instance on
        :return: Result of running :class:`State` instance with ``a`` as state
        """
        return self.f(a)

    __call__ = run

    def map(self, f: Callable[[B], C]) -> 'State[C, A]':
        def _(b: B, a: A):
            return f(b), a

        return State(lambda a: _(*self(a)))


def put(a: A) -> State[None, A]:
    """
    Update the state in the current computation

    :example:
    >>> put('state').run('')
    (), 'state'

    :param a: The new state
    :return: :class:`State` with ``a`` as the new state
    """
    return State(lambda state: (None, a))


def get() -> State[A, A]:
    """
    Get the current state

    :example:
    >>> get().run('state')
    'state', 'state'

    :return: :class:`State` with the current state as its result
    """
    return State(lambda b: (b, b))


def value(b: B) -> State[B, A]:
    """
    Put a value in the :class:`State` context

    :example:
    >>> value(1).run('state')
    1, 'state'

    :param b: the value to put in a :class:`State` context
    :return: :class:`State` that will produce ``b`` no matter the state
    """
    return State(lambda a: (b, a))
