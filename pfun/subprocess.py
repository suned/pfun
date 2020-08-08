import asyncio
from subprocess import PIPE, CalledProcessError
from typing import IO, Tuple, Union

from typing_extensions import Protocol

from .aio_trampoline import Done
from .effect import Effect, Try, add_repr, depend
from .either import Left, Right
from .functions import curry
from .immutable import Immutable


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
    ) -> Try[CalledProcessError, Tuple[bytes, bytes]]:
        """
        Get an `Effect` that runs `cmd` in the shell

        Example:
            >>> Subprocess().run_in_shell('cat foo.txt').run(None)
            (b'contents of foo.txt', b'')

        Args:
            cmd: the command to run
            stdin: input pipe for the subprocess
            stdout: output pipe for the subprocess
            stderr: error pipe for the subprocess
        Return:
            `Effect` that runs `cmd` in the shell and produces \
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
    """
    subprocess: Subprocess
    """
    The provided `Subprocess` module
    """


@curry
@add_repr
def run_in_shell(
    cmd: str,
    stdin: Union[IO, int] = PIPE,
    stdout: Union[IO, int] = PIPE,
    stderr: Union[IO, int] = PIPE
) -> Effect[HasSubprocess, CalledProcessError, Tuple[bytes, bytes]]:
    """
    Get an `Effect` that runs `cmd` in the shell

    Example:
        >>> class Env:
        ...     subprocess = Subprocess()
        >>> run_in_shell('cat foo.txt').run(Env())
        (b'contents of foo.txt', b'')

    Args:
        cmd: the command to run
        stdin: input pipe for the subprocess
        stdout: output pipe for the subprocess
        stderr: error pipe for the subprocess
    Return:
        `Effect` that runs `cmd` in the shell and produces \
        a tuple of `(stdout, stderr)`
    """
    return depend(HasSubprocess).and_then(
        lambda env: env.subprocess.run_in_shell(cmd, stdin, stdout, stderr)
    )
