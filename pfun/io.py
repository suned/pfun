from typing import (
    Generic,
    TypeVar,
    Callable,
    Tuple,
    cast,
    IO as TextIO,
    Optional,
    Iterable,
    cast
)
import sys
from functools import wraps

from .immutable import Immutable
from .curry import curry
from .monad import Monad, sequence_, map_m_, filter_m_

A = TypeVar('A')
B = TypeVar('B')


def pure_print(world: int, text: str, file_: TextIO) -> int:
    print(text, file=file_)
    return world + 1


def pure_input(world: int, message: Optional[str]) -> Tuple[int, str]:
    text = input(message)
    return (world + 1, text)


class IO(Generic[A], Monad, Immutable):
    """
    Pure IO value
    """
    a: A

    def and_then(self, f: 'Callable[[A], IO[B]]') -> 'IO[B]':
        return f(self.a)

    def map(self, f: Callable[[A], B]) -> 'IO[B]':
        return IO(f(self.a))

    def run(self, world: int = 0) -> A:
        return self.a


class Put(IO[Tuple[str, IO[A]]]):
    a: Tuple[str, IO[A]]
    file_: TextIO = sys.stdout

    def and_then(self, f: Callable[[A], IO[B]]) -> IO[B]:  # type: ignore
        text, action = self.a
        new = (text, action.and_then(f))
        return cast(IO[B], Put(new))

    def map(self, f: Callable[[A], B]) -> IO[B]:  # type: ignore
        text, action = self.a
        return Put((text, action.map(f)))  # type: ignore

    def run(self, world: int = 0) -> A:  # type: ignore
        text, action = self.a
        new_world = pure_print(world, text, self.file_)
        return action.run(new_world)


class Get(IO[Callable[[str], IO[A]]]):
    a: Callable[[str], IO[A]]
    message: str = ''

    def and_then(self, f: Callable[[A], IO[B]]) -> IO[B]:  # type: ignore
        return Get(  # type: ignore
            lambda text: self.a(text).and_then(f), self.message  # type: ignore
        )

    def map(self, f: Callable[[A], B]) -> IO[B]:  # type: ignore
        return Get(  # type: ignore
            lambda text: self.a(text).map(f), self.message  # type: ignore
        )

    def run(self, world: int = 0) -> A:  # type: ignore
        new_world, text = pure_input(world, self.message)
        action = self.a(text)  # type: ignore
        return action.run(new_world)


class ReadFile(IO[Tuple[str, Callable[[str], IO[A]]]]):
    a: Tuple[str, Callable[[str], IO[A]]]
    mode: str = 'r'

    def and_then(self, f: Callable[[A], IO[B]]) -> IO[B]:  # type: ignore
        filename, g = self.a
        return ReadFile((filename, lambda s: g(s).and_then(f)))  # type: ignore

    def map(self, f: Callable[[A], B]) -> IO[B]:  # type: ignore
        filename, g = self.a
        return Get(lambda text: g(text).map(f))  # type: ignore

    def run(self, world: int = 0) -> A:  # type: ignore
        filename, g = self.a
        with open(filename, self.mode) as f:
            data = f.read()
        action = g(data)
        return action.run(world + 1)


class WriteFile(IO[Tuple[str, str, IO[A]]]):
    a: Tuple[str, str, IO[A]]
    mode: str = 'w'

    def and_then(self, f: Callable[[A], IO[B]]) -> IO[B]:  # type: ignore
        filename, content, action = self.a
        return WriteFile(  # type: ignore
            (filename, content, action.and_then(f)))

    def map(self, f: Callable[[A], B]) -> IO[B]:  # type: ignore
        filename, content, action = self.a
        return WriteFile((filename, content, action.map(f)))  # type: ignore

    def run(self, world: int = 0) -> A:  # type: ignore
        filename, content, action = self.a
        with open(filename, self.mode) as f:
            f.write(content)
        return action.run(world + 1)


def get_line(message: str = '') -> IO[str]:
    """
    Create an :class:`IO` action that reads a line from standard input
    when run

    :param message: The message to display to the user
    :return: :class:`IO` action with the line read from standard in
    """
    return Get(lambda text: IO(text), message)  # type: ignore


@curry
def put_line(string: str = None, file=sys.stdout) -> IO[None]:
    """
    Print a line to standard out

    :param string: The line to print
    :param file: The file to print to (`sys.stdout` by default)
    :return: :class:`IO` action that prints `string` to standard out
    """
    return Put((string, IO(None)), file_=file)  # type: ignore


def read_file(filename: str) -> IO[str]:
    """
    Read the contents of a file as a `str`

    :param filename: the name of the file
    :return: :class:`IO` action with the contents of `filename`
    """
    return ReadFile((filename, lambda text: IO(text)))  # type: ignore


@curry
def write_file(filename: str, content: str) -> IO[None]:
    """
    Write a `str` to a file

    :param filename: the file to write to
    :param content: the content to write to the file
    :return: :class:`IO` action that produces \
        the content of `filename` when run
    """
    return WriteFile((filename, content, IO(None)))  # type: ignore


@curry
def write_file_bytes(filename: str, content: bytes) -> IO[None]:
    """
    Write `bytes` to a file

    :param filename: the file to write to
    :param content: the `bytes` to write to the file
    :return: :class:`IO` action that writes to the file when run
    """
    return WriteFile((filename, content, IO(None)), mode='wb')  # type: ignore


def read_file_bytes(filename: str) -> IO[bytes]:
    """
    Read the contents of a file as `bytes`

    :param filename: the filename to read bytes from
    :return: :class:`IO` action that reads the `bytes` of the file when run
    """
    return ReadFile(  # type: ignore
        (filename, lambda text: IO(text)), mode='rb')


def io(f: Callable[..., A]) -> Callable[..., IO[A]]:
    """
    Decorator to turn any non-monadic function into a monadic
    one by wrapping its result in :class:`IO`

    :param f: The function to wrap
    :return: `f` wrapped by :class:`IO`
    """
    @wraps(f)
    def decorator(*args, **kwargs):
        v = f(*args, **kwargs)
        return IO(v)

    return decorator


@curry
def map_m(f: Callable[[A], IO[B]], iterable: Iterable[A]) -> IO[Iterable[B]]:
    """
    Map each in element in ``iterable`` to
    an :class:`IO` by applying ``f``,
    combine the elements by ``and_then``
    from left to right and collect the results

    :example:
    >>> map_m(IO, range(3))
    IO(a=(0, 1, 2))

    :param f: Function to map over ``iterable``
    :param iterable: Iterable to map ``f`` over
    :return: ``f`` mapped over ``iterable`` and combined from left to right.
    """
    return cast(IO[Iterable[B]], map_m_(IO, f, iterable))


def sequence(iterable: Iterable[IO[A]]) -> IO[Iterable[A]]:
    """
    Evaluate each :class:`IO` in `iterable` from left to right
    and collect the results

    :example:
    >>> sequence([IO(v) for v in range(3)])
    Just(a=(0, 1, 2))

    :param iterable: The iterable to collect results from
    :returns: ``Maybe`` of collected results
    """
    return cast(IO[Iterable[A]], sequence_(IO, iterable))


@curry
def filter_m(f: Callable[[A], IO[bool]],
             iterable: Iterable[A]) -> IO[Iterable[A]]:
    """
    Map each element in ``iterable`` by applying ``f``,
    filter the results by the value returned by ``f``
    and combine from left to right.

    :example:
    >>> filter_m(lambda v: IO(v % 2 == 0), range(3))
    IO(a=(0, 2))

    :param f: Function to map ``iterable`` by
    :param iterable: Iterable to map by ``f``
    :return:
    """
    return cast(IO[Iterable[A]], filter_m_(IO, f, iterable))


__all__ = [
    'IO',
    'get_line',
    'put_line',
    'read_file',
    'write_file_bytes',
    'write_file',
    'read_file_bytes',
    'io',
    'map_m',
    'sequence',
    'filter_m'
]
