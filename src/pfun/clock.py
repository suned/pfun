import asyncio
import datetime

from typing_extensions import Protocol

from .effect import Success, from_callable, Depends, depend, from_awaitable
from .either import Right
from .immutable import Immutable


class Clock(Immutable):
    def sleep(self, seconds: float) -> Success[None]:
        return from_awaitable(asyncio.sleep(seconds))

    def now(self, tz: datetime.tzinfo = None) -> Success[datetime.datetime]:
        def _(_) -> Right[datetime.datetime]:
            return Right(datetime.datetime.now(tz))

        return from_callable(_)


class HasClock(Protocol):
    clock: Clock


def sleep(seconds: float) -> Depends[HasClock, None]:
    return depend().and_then(lambda env: env.clock.sleep(seconds)).with_repr(f"sleep({seconds})")


def now(tz: datetime.tzinfo = None) -> Depends[HasClock, datetime.datetime]:
    return depend().and_then(lambda env: env.clock.now(tz)).with_repr(f"now({tz})")