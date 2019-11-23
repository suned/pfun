from typing import Any
from typing_extensions import Protocol
import asyncio

from . import Effect, Never, get_environment
from ..immutable import Immutable
from ..either import Either, Right
from ..aio_trampoline import Trampoline, Done

_print = print
_input = input


class Console(Immutable):
    def print(self, msg: str = '') -> Effect[Any, Never, None]:
        async def run_e(_) -> Trampoline[Either[Never, None]]:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, _print, msg)
            return Done(Right(None))

        return Effect(run_e)

    def input(self, prompt: str = '') -> Effect[Any, Never, str]:
        async def run_e(_):
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, _input, prompt)
            return Done(Right(result))

        return Effect(run_e)


class HasConsole(Protocol):
    """
    Protocol module providing the `console` capability

    :type console: Console
    :attribute console: The instance of the console
    """
    console: Console


def print(msg: str = '') -> Effect[HasConsole, Never, None]:
    return get_environment().and_then(lambda env: env.console.print(msg))


def input(prompt: str = '') -> Effect[HasConsole, Never, str]:
    return get_environment().and_then(lambda env: env.console.input(prompt))
