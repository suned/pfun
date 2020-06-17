from typing import Any, NoReturn
from typing_extensions import Protocol
import asyncio

from .effect import Effect, get_environment
from ..immutable import Immutable
from ..either import Either, Right
from ..aio_trampoline import Trampoline, Done


class Console(Immutable):
    """
    Module that enables printing to stdout and reading from stdin
    """
    def print(self, msg: str = '') -> Effect[Any, NoReturn, None]:
        """
        Get an effect that prints to stdout

        :example:
        >>> Console().print('Hello pfun!').run(None)
        Hello pfun!

        :param msg: Message to print
        :return: :class:`Effect` that prints `msg` to stdout
        """
        async def run_e(_) -> Trampoline[Either[NoReturn, None]]:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, print, msg)
            return Done(Right(None))

        return Effect(run_e)

    def input(self, prompt: str = '') -> Effect[Any, NoReturn, str]:
        """
        Get an effect that reads from stdin

        :example:
        >>> Console().input('What is your name? ').map(lambda name: f'Hello {name}').run(None)
        what is your name?  # input e.g "John Doe"
        'Hello John Doe!'

        :param prompt: Prompt to dislay on stdout
        :return: :class:`Effect` that reads from stdin
        """
        async def run_e(_):
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, input, prompt)
            return Done(Right(result))

        return Effect(run_e)


class HasConsole(Protocol):
    """
    Module provider providing the `console` module

    :type console: Console
    :attribute console: The instance of the console
    """
    console: Console


def print_line(msg: str = '') -> Effect[HasConsole, NoReturn, None]:
    """
    Get an :class:`Effect` that prints to the console and succeeds with `None`

    :example:
    >>> class Env:
    ...     console = Console()
    >>> print_line('Hello pfun!').run(Env())
    Hello pfun!

    :param msg: Message to print
    :return: :class:`Effect` that prints to the console using the :class:`HasConsole` provided to `run`
    """
    return get_environment().and_then(lambda env: env.console.print(msg))


def get_line(prompt: str = '') -> Effect[HasConsole, NoReturn, str]:
    """
    Get an :class:`Effect` that reads a `str` from stdin

    :example:
    >>> class Env:
    ...     console = Console()
    >>> get_line('What is your name? ').map(lambda name: f'Hello {name}!').run(Env())
    name?  # input e.g 'John Doe'
    'Hello John Doe!'

    :param prompt: prompt to display in console
    :return: an :class:`Effect` that produces a `str` read from stdin
    """
    return get_environment().and_then(lambda env: env.console.input(prompt))
