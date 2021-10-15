import random as random_

from typing_extensions import Protocol

from .effect import Depends, Success, depend, purify
from .immutable import Immutable


class Random(Immutable):
    """
    Module that provides random number generation
    """
    def randint(self, a: int, b: int) -> Success[int]:
        """
        Create an `Effect` that succeeds with a random integer `n` \
        in the range `a <= n <= b`.

        Args:
            a: lower bound
            b: upper bound
        Return:
            `Effect` that succeeds with a random integer
        """
        return purify(random_.randint)(a, b)

    def random(self) -> Success[float]:
        """
        Create an `Effect` that succeeds with a random float between \
        0.0 and 1.0

        Return:
            `Effect` that succeeds with a random float
        """
        return purify(random_.random)()


class HasRandom(Protocol):
    """
    Module provider for the random module

    Attributes:
        random: The random module
    """
    random: Random


def randint(a: int, b: int) -> Depends[HasRandom, int]:
    """
    Create an `Effect` that succeeds with a random integer `n` in the range \
    `a <= n <= b`.

    Example:
        >>> from pfun import DefaultModules
        >>> randint(0, 1).run(DefaultModules())
        0
    Args:
        a: lower bound
        b: upper bound
    Return:
        `Effect` that succeeds with a random integer
    """
    return depend(HasRandom).and_then(
        lambda env: env.random.randint(a, b)
    ).with_repr(f'randint({repr(a)}, {repr(b)})')


def random() -> Depends[HasRandom, float]:
    """
    Create an `Effect` that succeeds with a random float between 0.0 and 1.0

    Example:
        >>> from pfun import DefaultModules
        >>> random().run(DefaultModules)
        0.575351197
    Return:
        `Effect` that succeeds with a random float
    """
    return depend().and_then(
        lambda env: env.random.random()
    ).with_repr('random()')
