import random as random_

from typing_extensions import Protocol

from .effect import Success, lift, catch, Depends, depend
from .immutable import Immutable


class Random(Immutable):
    def randint(self, a: int, b: int) -> Success[int]:
        return catch(Exception)(lambda: random_.randint(a, b))()

    def random(self) -> Success[float]:
        return catch(Exception)(lambda: random_.random())()


class HasRandom(Protocol):
    random: Random


def randint(a, b) -> Depends[HasRandom, int]:
    return depend(HasRandom).and_then(lambda env: env.random.randint(a, b))


def random() -> Depends[HasRandom, float]:
    return depend().and_then(lambda env: env.random.random())
