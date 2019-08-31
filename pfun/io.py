from typing import Generic, TypeVar, Callable, Tuple, cast

from .immutable import Immutable

A = TypeVar('A')
B = TypeVar('B')


def pure_print(world: int, text: str) -> int:
    print(text)
    return world + 1


def pure_input(world: int) -> Tuple[int, str]:
    text = input()
    return (world + 1, text)


class IO(Generic[A], Immutable):
    a: A

    def and_then(self, f: 'Callable[[A], IO[B]]') -> 'IO[B]':
        return f(self.a)

    def run(self, world: int = 0) -> A:
        return self.a


class Put(IO[Tuple[str, IO[A]]]):
    a: Tuple[str, IO[A]]

    def and_then(self, f: Callable[[A], IO[B]]) -> IO[B]:  # type: ignore
        text, action = self.a
        new = (text, action.and_then(f))  # type: ignore
        return cast(IO[B], Put(new))

    def run(self, world: int = 0) -> A:  # type: ignore
        text, action = self.a
        new_world = pure_print(world, text)
        return action.run(new_world)


class Get(IO[Callable[[str], IO[A]]]):
    a: Callable[[str], IO[A]]

    def and_then(self, f: Callable[[A], IO[B]]) -> IO[B]:  # type: ignore
        return Get(lambda text: self.a(text).and_then(f))  # type: ignore

    def run(self, world: int = 0) -> A:  # type: ignore
        new_world, text = pure_input(world)
        action = self.a(text)  # type: ignore
        return action.run(new_world)


class ReadFile(IO[Tuple[str, Callable[[str], IO[A]]]]):
    a: Tuple[str, Callable[[str], IO[A]]]
    mode: str = 'r'

    def and_then(self, f: Callable[[A], IO[B]]) -> IO[B]:  # type: ignore
        filename, g = self.a
        return ReadFile(filename, lambda s: g(s).and_then(f))  # type: ignore

    def run(self, world: int = 0) -> A:  # type: ignore
        filename, g = self.a
        with open(filename, self.mode) as f:
            data = f.read()
        action = g(data)
        return action.run(world + 1)


def get_line() -> IO[str]:
    return Get(lambda text: IO(text))  # type: ignore


def put_line(string: str = None) -> IO[None]:
    return Put((string, IO(None)))  # type: ignore


def read_file(filename: str) -> IO[str]:
    return ReadFile((filename, lambda text: IO(text)))  # type: ignore


def read_file_bytes(filename: str) -> IO[bytes]:
    return ReadFile(  # type: ignore
        (filename, lambda text: IO(text)), mode='rb')
