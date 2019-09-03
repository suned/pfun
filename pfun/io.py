from typing import (Generic, TypeVar, Callable, Tuple, cast, IO as TextIO,
                    Optional)
import sys
from functools import wraps

from .immutable import Immutable
from .curry import curry

A = TypeVar('A')
B = TypeVar('B')


def pure_print(world: int, text: str, file_: TextIO) -> int:
    print(text, file=file_)
    return world + 1


def pure_input(world: int, message: Optional[str]) -> Tuple[int, str]:
    text = input(message)
    return (world + 1, text)


class IO(Generic[A], Immutable):
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
        new = (text, action.and_then(f))  # type: ignore
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
    message: Optional[str] = None

    def and_then(self, f: Callable[[A], IO[B]]) -> IO[B]:  # type: ignore
        return Get(lambda text: self.a(text).and_then(f))  # type: ignore

    def map(self, f: Callable[[A], B]) -> IO[B]:  # type: ignore
        return Get(lambda text: self.a(text).map(f))  # type: ignore

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


def get_line(message: Optional[str] = None) -> IO[str]:
    return Get(lambda text: IO(text), message)  # type: ignore


def put_line(string: str = None, file=sys.stdout) -> IO[None]:
    return Put((string, IO(None)), file_=file)  # type: ignore


def read_file(filename: str) -> IO[str]:
    return ReadFile((filename, lambda text: IO(text)))  # type: ignore


@curry
def write_file(filename: str, content: str) -> IO[None]:
    return WriteFile((filename, content, IO(None)))  # type: ignore


@curry
def write_file_bytes(filename: str, content: bytes) -> IO[None]:
    return WriteFile((filename, content, IO(None)), mode='wb')  # type: ignore


def read_file_bytes(filename: str) -> IO[bytes]:
    return ReadFile(  # type: ignore
        (filename, lambda text: IO(text)), mode='rb')


def io(f: Callable[..., A]) -> Callable[..., IO[A]]:
    @wraps(f)
    def decorator(*args, **kwargs):
        v = f(*args, **kwargs)
        return IO(v)

    return decorator
