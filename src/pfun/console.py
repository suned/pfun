from __future__ import annotations

from typing import NoReturn

from typing_extensions import Protocol

from .effect import Effect, Success, add_repr, depend, purify_io_bound
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
        return purify_io_bound(print)(msg)

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
        return purify_io_bound(input)(prompt)


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
    return depend(HasConsole).and_then(lambda env: env.console.print(msg))


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
    return depend(HasConsole).and_then(lambda env: env.console.input(prompt))
