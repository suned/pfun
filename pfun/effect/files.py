from typing import Any, Protocol

from . import Effect, get_environment
from ..either import Either, Left, Right
from ..aio_trampoline import Done, Trampoline
from ..immutable import Immutable
from ..curry import curry
import sys


class Files(Immutable):
    def read(self, path: str) -> Effect[Any, IOError, str]:
        async def run_e(_) -> Trampoline[Either[IOError, str]]:
            try:
                with open(path) as f:
                    contents = f.read()
                return Done(Right(contents))
            except IOError as e:
                return Done(Left(e))

        return Effect(run_e)

    def read_bytes(self, path: str) -> Effect[Any, IOError, bytes]:
        async def run_e(_) -> Trampoline[Either[IOError, bytes]]:
            try:
                with open(path, 'b') as f:
                    contents = f.read()
                return Done(Right(contents))
            except IOError as e:
                return Done(Left(e))

        return Effect(run_e)

    def write(self, path: str, content: str) -> Effect[Any, IOError, None]:
        async def run_e(_) -> Trampoline[Either[IOError, None]]:
            try:
                with open(path, 'w') as f:
                    f.write(content)
                return Done(Right(None))
            except IOError as e:
                return Done(Left(e))

        return Effect(run_e)

    def write_bytes(self, path: str,
                    content: bytes) -> Effect[Any, IOError, None]:
        pass

    def append(self, path: str, content: str) -> Effect[Any, IOError, None]:
        pass

    def append_bytes(self, path: str,
                     content: bytes) -> Effect[Any, IOError, None]:
        pass


class HasFiles(Protocol):
    files: Files


def read(path: str) -> Effect[HasFiles, IOError, str]:
    return get_environment().and_then(lambda env: env.files.read(path))


@curry
def write(path: str, content: str) -> Effect[HasFiles, IOError, None]:
    return get_environment(
    ).and_then(lambda env: env.files.write(path, content))
