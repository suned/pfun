from dataclasses import dataclass
from functools import WRAPPER_ASSIGNMENTS, WRAPPER_UPDATES
from typing import TypeVar, Callable

from .util import compose

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')


@dataclass(frozen=True, repr=False)
class Pipe(Callable[[A], B]):
    f: Callable[[A], B]

    def __post_init__(self):
        # mimic functools.update_wrapper
        for attr in WRAPPER_ASSIGNMENTS:
            try:
                value = getattr(self.f, attr)
            except AttributeError:
                pass
            else:
                object.__setattr__(self, attr, value)
        for attr in WRAPPER_UPDATES:
            getattr(self, attr).update(getattr(self.f, attr, {}))

    def and_then(self, other: Callable[[B], C]) -> 'Pipe[A, C]':
        return Pipe(compose(other, self.f))

    def __rrshift__(self, other: A) -> B:
        return self(other)

    def __call__(self, a: A) -> B:
        return self.f(a)

    def __repr__(self):
        return repr(self.f)


def pipe(f: Callable[[A], B]) -> Pipe[A, B]:
    return Pipe(f)
