import asyncio
from typing import NoReturn

from typing_extensions import Protocol

from .aio_trampoline import Done, Trampoline
from .effect import Effect, Success, add_repr, get_environment
from .either import Either, Right
from .immutable import Immutable


class Console(Immutable):
    """
    Module that enables printing to stdout and reading from stdin
    """
    def print(self, msg: str = '') -> Success[None]:
        """
        Get an effect that prints to stdout

        Example:
            >>> Console().print('Hello pfun!').run(None)
            Hello pfun!

        Args:
            msg: Message to print

        Return:
            `Effect` that prints `msg` to stdout
        """
        async def run_e(_) -> Trampoline[Either[NoReturn, None]]:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, print, msg)
            return Done(Right(None))

        return Effect(run_e)

    def input(self, prompt: str = '') -> Success[str]:
        """
        Get an effect that reads from stdin

        Example:
            >>> greeting = lambda name: f'Hello {name}'
            >>> Console().input('What is your name? ').map(greeting).run(None)
            what is your name?  # input e.g "John Doe"
            'Hello John Doe!'

        Args:
            prompt: Prompt to dislay on stdout

        Return:
            `Effect` that reads from stdin
        """
        async def run_e(_):
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, input, prompt)
            return Done(Right(result))

        return Effect(run_e)


class HasConsole(Protocol):
    """
    Module provider providing the `console` module
    """
    console: Console
    """
    The provided `Console`
    """


@add_repr
def print_line(msg: str = '') -> Effect[HasConsole, NoReturn, None]:
    """
    Get an `Effect` that prints to the console and succeeds with `None`

    Example:
        >>> class Env:
        ...     console = Console()
        >>> print_line('Hello pfun!').run(Env())
        Hello pfun!

    Args:
        msg: Message to print

    Return:
        `Effect` that prints to the console using the \
        `HasConsole` provided to `run`
    """
    return get_environment(HasConsole
                           ).and_then(lambda env: env.console.print(msg))


@add_repr
def get_line(prompt: str = '') -> Effect[HasConsole, NoReturn, str]:
    """
    Get an `Effect` that reads a `str` from stdin

    Example:
        >>> class Env:
        ...     console = Console()
        >>> greeting = lambda name: f'Hello {name}!'
        >>> get_line('What is your name? ').map(greeting).run(Env())
        name?  # input e.g 'John Doe'
        'Hello John Doe!'

    Args:
        prompt: prompt to display in console

    Return:
        an `Effect` that produces a `str` read from stdin
    """
    return get_environment(HasConsole
                           ).and_then(lambda env: env.console.input(prompt))
