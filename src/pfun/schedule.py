"""

Attributes:
    Schedule (TypeAlias): Type-alias for \
        `Effect[TypeVar('R'), NoReturn, Iterator[datetime.timedelta]]`
"""

from __future__ import annotations

import itertools
from datetime import timedelta
from typing import Callable, Iterator, NoReturn, TypeVar

from . import Intersection
from .effect import Effect, lift, success
from .functions import curry
from .random import HasRandom, random

R = TypeVar('R')

Schedule = Effect[R, NoReturn, Iterator[timedelta]]


def spaced(delta: timedelta) -> Schedule[object]:
    """
    Create a schedule that repeats `delta` forever.
    Args:
        delta: time interval to repeat
    Return:
        Schedule that repeats `delta` forever
    """
    return success(itertools.repeat(delta)).with_repr(f'spaced({repr(delta)})')


def exponential(delta: timedelta) -> Schedule[object]:
    """
    Create a schedule that increases time intervals exponentially forever,
    starting from `delta`

    Args:
        delta: base interval to increase exponentially
    Return:
        Schedule that increases exponentially forever
    """
    exp = lambda step: timedelta(seconds=delta.total_seconds() * (2.0 ** step))
    return success(
        map(exp, itertools.count())
    ).with_repr(
        f'exponential({repr(delta)})'
    )


@curry
def recurs(n: int, schedule: Schedule[R]) -> Schedule[R]:
    """
    Create a schedule that consumes `n` steps from `schedule`.
    If `schedule` is exhausted in less than `n` steps,
    the resulting schedule is also exhausted.

    Args:
        n: Number of steps to consume from `schedule`
        schedule: Schedule to consume intervals from
    Return:
        Schedule that consumes `n` steps from `schedule`, or all intervals \
        from `schedule`
    """
    return schedule.map(
        lambda deltas: itertools.islice(deltas, n)
    ).with_repr(
        f'recurs({n}, {repr(schedule)})'
    )


@curry
def take_while(p: Callable[[timedelta], bool],
               schedule: Schedule[R]) -> Schedule[R]:
    """
    Create a schedule that consumes intervals from `schedule` \
    until `p` returns `False`.

    Args:
        p: Predicate to test intervals from `schedule` with
        schedule: Schedule to consume intervals from
    Return:
        Schedule that consumes intervals from `schedule` until `p` \
        returns `False`
    """
    return schedule.map(
        lambda deltas: itertools.takewhile(p, deltas)
    ).with_repr(
        f'take_while({repr(p)}, {repr(schedule)})'
    )


@curry
def until(delta: timedelta, schedule: Schedule[R]) -> Schedule[R]:
    """
    Create a schedule that consumes intervals from `schedule` until an \
    interval is greater than `delta`.

    Args:
        delta: Max interval
        schedule: Schedule to consume intervals from
    Return:
        Schedule that consumes intervals from `schedule` until an interval \
        is greater than `delta`
    """
    return take_while(
        lambda d: d < delta,
        schedule
    ).with_repr(
        f'until({repr(delta)}, {repr(schedule)})'
    )


def jitter(schedule: Schedule[R]) -> Schedule[Intersection[R, HasRandom]]:
    """
    Create a schedule that randomly adds between 0 and 1 second to intervals \
    in `schedule`

    Args:
        schedule: Schedule to which random delays are added
    Return:
        Schedule that consumes from `schedule` and adds between 0 and 1 \
        second randomly
    """
    add_jitter = lift(
        lambda r, deltas: map(
            lambda d: timedelta(seconds=d.total_seconds() + r),
            deltas
        )
    )
    return add_jitter(random(), schedule).with_repr(
        f'jitter({repr(schedule)})')
