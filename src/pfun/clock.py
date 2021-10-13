import asyncio
import datetime

from typing_extensions import Protocol

from .effect import Depends, Success, depend, from_awaitable, purify
from .immutable import Immutable


class Clock(Immutable):
    """
    Module providing clock capabilities.
    """
    def sleep(self, seconds: float) -> Success[None]:
        """
        Create an `Effect` that Suspends execution for `seconds`.
        Args:
            seconds: interval to suspend execution
        Return:
            `Effect` that suspends execution for `seconds`
        """
        return from_awaitable(asyncio.sleep(seconds))

    def now(self, tz: datetime.tzinfo = None) -> Success[datetime.datetime]:
        """
        Create an `Effect` that succeeds with the current datetime

        Args:
            tz: timezone info
        Return:
            `Effect` that succeeds with the current datetime
        """
        return purify(datetime.datetime.now)(tz)


class HasClock(Protocol):
    """
    Module provider for the clock capability.

    Attributes:
        clock: The clock module
    """
    clock: Clock


def sleep(seconds: float) -> Depends[HasClock, None]:
    """
    Create an `Effect` that Suspends execution for `seconds`.
    Example:
        >>> from pfun import DefaultModules
        >>> sleep(2).run(DefaultModules)
    Args:
        seconds: interval to suspend execution
    Return:
        `Effect` that suspends execution for `seconds`
    """
    return depend().and_then(lambda env: env.clock.sleep(seconds)).with_repr(f"sleep({seconds})")


def now(tz: datetime.tzinfo = None) -> Depends[HasClock, datetime.datetime]:
    """
    Create an `Effect` that succeeds with the current datetime
    Example:
        >>> from pfun import DefaultModules
        >>> now().run(DefaultModules)
    Args:
        tz: timezone info
    Return:
        `Effect` that succeeds with the current datetime
    """
    return depend().and_then(lambda env: env.clock.now(tz)).with_repr(f"now({tz})")
