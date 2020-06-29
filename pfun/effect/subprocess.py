import asyncio
from subprocess import PIPE, CalledProcessError
from typing import IO, Any, Tuple, Union

from typing_extensions import Protocol

from ..aio_trampoline import Done
from ..either import Left, Right
from ..immutable import Immutable
from .effect import Effect, get_environment


class Subprocess(Immutable):
    """
    Module that enables running commands in the shell
    """
    def run_in_shell(
        self,
        cmd: str,
        stdin: Union[IO, int] = PIPE,
        stdout: Union[IO, int] = PIPE,
        stderr: Union[IO, int] = PIPE
    ) -> Effect[Any, CalledProcessError, Tuple[bytes, bytes]]:
        """
        Get an :class:`Effect` that runs `cmd` in the shell

        :example:
        >>> Subprocess().run_in_shell('cat foo.txt').run(None)
        (b'contents of foo.txt', b'')

        :param cmd: the command to run
        :param stdin: input pipe for the subprocess
        :param stdout: output pipe for the subprocess
        :param stderr: error pipe for the subprocess
        :return: :class:`Effect` that runs `cmd` in the shell and produces \
        a tuple of `(stdout, stderr)`
        """
        async def run_e(self):
            proc = await asyncio.create_subprocess_shell(
                cmd, stdin=stdin, stdout=stdout, stderr=stderr
            )
            stdout_, stderr_ = await proc.communicate()
            if proc.returncode != 0:
                return Done(
                    Left(
                        CalledProcessError(
                            proc.returncode, cmd, stdout_, stderr_
                        )
                    )
                )
            return Done(Right((stdout_, stderr_)))

        return Effect(run_e)


class HasSubprocess(Protocol):
    """
    Module provider providing the subprocess module

    :attribute subprocess: the :class:`Subprocess` instance
    """
    subprocess: Subprocess


def run_in_shell(
    cmd: str,
    stdin: Union[IO, int] = PIPE,
    stdout: Union[IO, int] = PIPE,
    stderr: Union[IO, int] = PIPE
) -> Effect[HasSubprocess, CalledProcessError, Tuple[bytes, bytes]]:
    """
    Get an :class:`Effect` that runs `cmd` in the shell

    :example:
    >>> class Env:
    ...     subprocess = Subprocess()
    >>> run_in_shell('cat foo.txt').run(Env())
    (b'contents of foo.txt', b'')

    :param cmd: the command to run
    :param stdin: input pipe for the subprocess
    :param stdout: output pipe for the subprocess
    :param stderr: error pipe for the subprocess
    :return: :class:`Effect` that runs `cmd` in the shell and produces \
        a tuple of `(stdout, stderr)`
    """
    return get_environment().and_then(
        lambda env: env.subprocess.run_in_shell(cmd, stdin, stdout, stderr)
    )
