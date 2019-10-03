from __future__ import annotations
from typing import Callable, TypeVar, Generic
import sys

from typing_extensions import Literal

from .immutable import Immutable
from .trampoline import Trampoline, Done, Call
from .monad import sequence_
from .curry import curry

A = TypeVar('A')
B = TypeVar('B')


class IO(Immutable, Generic[A]):
    """
    Represents world changing actions
    """
    run_io: Callable[[], Trampoline[A]]

    def and_then(self, f: Callable[[A], IO[B]]) -> IO[B]:
        def run() -> Trampoline[B]:
            def thunk():
                t = self.run_io()
                return t.and_then(lambda a: Call(lambda: f(a).run_io()))

            return Call(thunk)

        return IO(run)

    def map(self, f: Callable[[A], B]) -> IO[B]:
        return IO(lambda: Call(lambda: self.run_io().map(f)))  # type: ignore

    def run(self):
        return self.run_io().run()


def value(a: A) -> IO[A]:
    """
    Create an :class:`IO` action that simply produces
    `a` when run

    :param a: The value to wrap in `IO`
    """
    return IO(lambda: Done(a))


def read_str(path: str) -> IO[str]:
    """
    Read the contents of a file as a `str`

    :param path: the name of the file
    :return: :class:`IO` action with the contents of `filename`
    """
    def run() -> Trampoline[str]:
        with open(path) as f:
            return Done(f.read())

    return IO(run)


# We pretend the next part doesn't exist...


@curry
def write_str(path: str, content: str,
              mode: Literal['w', 'a'] = 'w') -> IO[None]:
    """
    Write a `str` to a file

    :param path: the file to write to
    :param content: the content to write to the file
    :return: :class:`IO` action that produces \
        the content of `filename` when run
    """
    def run() -> Trampoline[None]:
        with open(path, mode) as f:
            f.write(content)
        return Done(None)

    return IO(run)


@curry
def write_bytes(path: str, content: bytes,
                mode: Literal['w', 'a'] = 'w') -> IO[None]:
    """
    Write `bytes` to a file

    :param filename: the file to write to
    :param content: the `bytes` to write to the file
    :return: :class:`IO` action that writes to the file when run
    """
    def run() -> Trampoline[None]:
        with open(path, mode + 'b') as f:
            f.write(content)
        return Done(None)

    return IO(run)


def put_line(line: str = '', file=sys.stdout) -> IO[None]:
    """
    Print a line to standard out

    :param string: The line to print
    :param file: The file to print to (`sys.stdout` by default)
    :return: :class:`IO` action that prints `string` to standard out
    """
    def run() -> Trampoline[None]:
        print(line)
        return Done(None)

    return IO(run)


def get_line(prompt: str = '') -> IO[str]:
    """
    Create an :class:`IO` action that reads a line from standard input
    when run

    :param prompt: The message to display to the user
    :return: :class:`IO` action with the line read from standard in
    """
    def run() -> Trampoline[str]:
        line = input(prompt)
        return Done(line)

    return IO(run)


def read_bytes(path: str) -> IO[bytes]:
    """
    Read the contents of a file as `bytes`

    :param path: the filename to read bytes from
    :return: :class:`IO` action that reads the `bytes` of the file when run
    """
    def run() -> Trampoline[bytes]:
        with open(path, 'rb') as f:
            return Done(f.read())

    return IO(run)


def sequence(ios):
    return sequence_(value, ios)
