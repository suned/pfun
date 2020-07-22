from abc import ABC, abstractmethod
from functools import reduce
from typing import Any, Callable, Iterable

from .functions import curry
from .functor import Functor


class Monad(Functor, ABC):
    """
    Base class for all monadic types
    """
    @abstractmethod
    def and_then(self, f: Callable[[Any], Any]) -> 'Monad':
        pass


# Since PEP484 does not support higher-order type variables,
# the functions below cannot be typed here :(
# type versions for each monad is provided
# in their respective namespaces instead (e.g maybe.sequence)


@curry
def sequence_(
    value: Callable[[Any], Monad], iterable: Iterable[Monad]
) -> Monad:
    def combine(ms: Monad, m: Monad) -> Monad:
        return ms.and_then(
            lambda xs: m.and_then(
                lambda x: value(xs + (x, ))
            )
        )  # yapf: disable
    return reduce(combine, iterable, value(()))


@curry
def map_m_(
    value: Callable[[Any], Monad],
    f: Callable[[Any], Monad],
    iterable: Iterable
) -> Monad:
    m_iterable = (f(x) for x in iterable)
    return sequence_(value, m_iterable)


@curry
def filter_m_(
    value: Callable[[Any], Monad],
    f: Callable[[Any], Monad],
    iterable: Iterable
) -> Monad:
    def combine(ms, mbx):
        mb, x = mbx
        return ms.and_then(
            lambda xs: mb.and_then(lambda b: value(xs + (x, ) if b else xs))
        )

    mbs = (f(x) for x in iterable)
    mbxs = zip(mbs, iterable)
    return reduce(combine, mbxs, value(()))
