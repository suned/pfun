from typing import Any, NoReturn
from typing_extensions import Protocol
import asyncio

from . import Effect, get_environment
from ..immutable import Immutable
from ..either import Either, Right
from ..aio_trampoline import Trampoline, Done


class Console(Immutable):
    def print(self, msg: str = '') -> Effect[Any, NoReturn, None]:
        async def run_e(_) -> Trampoline[Either[NoReturn, None]]:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, print, msg)
            return Done(Right(None))

        return Effect(run_e)

    def input(self, prompt: str = '') -> Effect[Any, NoReturn, str]:
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


def print_line(msg: str = '') -> Effect[HasConsole, NoReturn, None]:
    return get_environment().and_then(lambda env: env.console.print(msg))


def get_line(prompt: str = '') -> Effect[HasConsole, NoReturn, str]:
    return get_environment().and_then(lambda env: env.console.input(prompt))
