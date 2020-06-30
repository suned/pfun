from __future__ import annotations

import sys
from functools import wraps
from typing import Callable, Generator, Generic, Iterable, TypeVar, cast

from typing_extensions import Literal

from .curry import curry
from .immutable import Immutable
from .monad import Monad, filter_m_, map_m_, sequence_
from .trampoline import Call, Done, Trampoline
from .with_effect import with_effect_

A = TypeVar('A')
B = TypeVar('B')


class IO(Monad, Immutable, Generic[A]):
    """
    Represents world changing actions
    """
    run_io: Callable[[], Trampoline[A]]

    def and_then(self, f: Callable[[A], IO[B]]) -> IO[B]:
        """
        Chain together functions producting world changing actions.

        :param f: function to compose with this action
        :return: new :class:`IO` action that that composes \
            this action with action produced by `f`

        :example:
        >>> read_str('file.txt').and_then(
        ...    lambda content: value(content.upper())
        ... ).run()
        "CONTENTS OF FILE.TXT"

        :param f: function to compose with this :class:`IO` action
        :return: new :class:`IO` action composed with f
        """
        def run() -> Trampoline[B]:
            def thunk() -> Trampoline[B]:
                t = self.run_io()  # type: ignore
                return t.and_then(
                    lambda a: Call(lambda: f(a).run_io())  # type: ignore
                )

            return Call(thunk)

        return IO(run)

    def map(self, f: Callable[[A], B]) -> IO[B]:
        """
        Map `f` over the value wrapped by this action

        :example:
        >>> read_str('file.txt').map(
        ...    lambda content: content.upper()
        ... ).run()
        "CONTENTS OF FILE.TXT"

        :param f: function to map over this :class:`IO` action
        :return: new :class:`IO` action with `f` applied to the \
            value wrapped by this one.
        """
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


@curry
def put_line(line: str = '', file=sys.stdout) -> IO[None]:
    """
    Print a line to standard out

    :param string: The line to print
    :param file: The file to print to (`sys.stdout` by default)
    :return: :class:`IO` action that prints `string` to standard out
    """
    def run() -> Trampoline[None]:
        print(line, file=file)
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
        return value(v)

    return decorator


@curry
def map_m(f: Callable[[A], IO[B]], iterable: Iterable[A]) -> IO[Iterable[B]]:
    """
    Map each in element in ``iterable`` to
    an :class:`IO` by applying ``f``,
    combine the elements by ``and_then``
    from left to right and collect the results

    :example:
    >>> map_m(IO, range(3)).run()
    (0, 1, 2)

    :param f: Function to map over ``iterable``
    :param iterable: Iterable to map ``f`` over
    :return: ``f`` mapped over ``iterable`` and combined from left to right.
    """
    return cast(IO[Iterable[B]], map_m_(value, f, iterable))


def sequence(iterable: Iterable[IO[A]]) -> IO[Iterable[A]]:
    """
    Evaluate each :class:`IO` in `iterable` from left to right
    and collect the results

    :example:
    >>> sequence([IO(v) for v in range(3)]).run()
    (0, 1, 2)

    :param iterable: The iterable to collect results from
    :returns: ``IO`` of collected results
    """
    return cast(IO[Iterable[A]], sequence_(value, iterable))


@curry
def filter_m(f: Callable[[A], IO[bool]],
             iterable: Iterable[A]) -> IO[Iterable[A]]:
    """
    Map each element in ``iterable`` by applying ``f``,
    filter the results by the value returned by ``f``
    and combine from left to right.

    :example:
    >>> filter_m(lambda v: IO(v % 2 == 0), range(3)).run()
    (0, 2)

    :param f: Function to map ``iterable`` by
    :param iterable: Iterable to map by ``f``
    :return: `iterable` mapped and filtered by `f`
    """
    return cast(IO[Iterable[A]], filter_m_(value, f, iterable))


IOs = Generator[IO[A], A, B]


def with_effect(f: Callable[..., IOs[A, B]]) -> Callable[..., IO[B]]:
    """
    Decorator for functions generating IOs. Will
    chain together the generated IOs using `and_then`

    :example:
    >>> @with_effect
    ... def put_file(path: str) -> IOs[str, None]:
    ...     content = yield read_str(path)
            yield put_line(content)
    >>> put_file('file.txt').run()
    Content of file.txt

    :param f: the function to decorate
    :return: new function that consumes `IO`s generated by `f`, \
        chaining them together with `and_then`
    """
    return with_effect_(value, f)  # type: ignore


__all__ = [
    'IO',
    'get_line',
    'put_line',
    'read_str',
    'write_bytes',
    'write_str',
    'read_bytes',
    'io',
    'map_m',
    'sequence',
    'filter_m',
    'with_effect',
    'IOs'
]
