from typing import Callable, Generator, Generic, Iterable, Tuple, TypeVar, cast

from .curry import curry
from .immutable import Immutable
from .monad import Monad, filter_m_, map_m_, sequence_
from .trampoline import Call, Done, Trampoline
from .with_effect import with_effect_

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')


class State(Generic[B, A], Immutable, Monad):
    """
    Represents a computation that is not yet complete,
    but will complete when given a state of type A
    """
    f: Callable[[A], Trampoline[Tuple[B, A]]]

    def and_then(self, f: 'Callable[[B], State[C, A]]') -> 'State[C, A]':
        """
        Chain together stateful computations

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
        return State(
            lambda a: Call(
                lambda: self.f(a).  # type: ignore
                and_then(
                    lambda tu: Call(lambda: f(tu[0]).f(tu[1]))  # type: ignore
                )
            )
        )

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
        return self.f(a).run()  # type: ignore

    def map(self, f: Callable[[B], C]) -> 'State[C, A]':
        return State(
            lambda a: self.f(a).  # type: ignore
            and_then(lambda tu: Done((f(tu[0]), tu[1])))
        )


def put(a: A) -> State[None, A]:
    """
    Update the current state

    :example:
    >>> put('state').run('')
    (), 'state'

    :param a: The new state
    :return: :class:`State` with ``a`` as the new state
    """
    return State(lambda state: Done((None, a)))


def get() -> State[A, A]:
    """
    Get the current state

    :example:
    >>> get().run('state')
    'state', 'state'

    :return: :class:`State` with the current state as its result
    """
    return State(lambda b: Done((b, b)))


def value(b: B) -> State[B, A]:
    """
    Put a value in the :class:`State` context

    :example:
    >>> value(1).run('state')
    1, 'state'

    :param b: the value to put in a :class:`State` context
    :return: :class:`State` that will produce ``b`` no matter the state
    """
    return State(lambda a: Done((b, a)))


@curry
def map_m(f: Callable[[A], State[A, B]],
          iterable: Iterable[A]) -> State[Iterable[A], B]:
    """
    Map each in element in ``iterable`` to
    an :class:`Maybe` by applying ``f``,
    combine the elements by ``and_then``
    from left to right and collect the results

    :example:
    >>> map_m(value, range(3)).run(None)
    ((0, 1, 2), None)

    :param f: Function to map over ``iterable``
    :param iterable: Iterable to map ``f`` over
    :return: ``f`` mapped over ``iterable`` and combined from left to right.
    """
    return cast(State[Iterable[A], B], map_m_(value, f, iterable))


def sequence(iterable: Iterable[State[A, B]]) -> State[Iterable[A], B]:
    """
    Evaluate each :class:`State` in `iterable` from left to right
    and collect the results

    :example:
    >>> sequence([value(v) for v in range(3)]).run(None)
    ((0, 1, 2), None)

    :param iterable: The iterable to collect results from
    :returns: ``Maybe`` of collected results
    """
    return cast(State[Iterable[A], B], sequence_(value, iterable))


@curry
def filter_m(f: Callable[[A], State[bool, B]],
             iterable: Iterable[A]) -> State[Iterable[A], B]:
    """
    Map each element in ``iterable`` by applying ``f``,
    filter the results by the value returned by ``f``
    and combine from left to right.

    :example:
    >>> filter_m(lambda v: value(v % 2 == 0), range(3)).Run(None)
    ((0, 2), None)

    :param f: Function to map ``iterable`` by
    :param iterable: Iterable to map by ``f``
    :return: `iterable` mapped and filtered by `f`
    """
    return cast(State[Iterable[A], B], filter_m_(value, f, iterable))


States = Generator[State[A, B], A, C]


def with_effect(f: Callable[..., States[A, B, C]]
                ) -> Callable[..., State[C, B]]:
    """
    Decorator for functions that
    return a generator of states and a final result.
    Iteraters over the yielded states and sends back the
    unwrapped values using "and_then"

    :example:
    >>> @with_effect
    ... def f() -> States[int, Any, int]:
    ...     a = yield value(2)
    ...     b = yield value(2)
    ...     return a + b
    >>> f().run(None)
    (4, None)

    :param f: generator function to decorate
    :return: `f` decorated such that generated :class:`State` \
        will be chained together with `and_then`
    """
    return with_effect_(value, f)  # type: ignore


__all__ = [
    'State',
    'put',
    'get',
    'value',
    'map_m',
    'sequence',
    'filter_m',
    'with_effect',
    'States'
]
