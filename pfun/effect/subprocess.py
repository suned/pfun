from typing import Any, Tuple, IO, Union
import asyncio
from subprocess import CalledProcessError, PIPE

from typing_extensions import Protocol

from ..immutable import Immutable
from ..aio_trampoline import Done
from ..either import Right, Left
from .effect import Effect, get_environment
from ..curry import curry


class Subprocess(Immutable):
    def run_in_shell(self, cmd: str, stdin: Union[IO, int] = PIPE, stdout: Union[IO, int] = PIPE, stderr: Union[IO, int] = PIPE) -> Effect[Any, CalledProcessError, Tuple[str, str]]:
        async def run_e(self):
            proc = await asyncio.create_subprocess_shell(cmd, stdin=stdin, stdout=stdout, stderr=stderr)
            stdout_, stderr_ = await proc.communicate()
            if proc.returncode != 0:
                return Done(Left(CalledProcessError(proc.returncode, cmd, stdout_, stderr_)))
            return Done(Right((stdout_, stderr_)))
        return Effect(run_e)

class HasSubprocess(Protocol):
    subprocess: Subprocess


def run_in_shell(cmd: str) -> Effect[HasSubprocess, CalledProcessError, Tuple[str, str]]:
    return get_environment().and_then(lambda env: env.subprocess.run_in_shell(cmd))
