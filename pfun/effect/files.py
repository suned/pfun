from typing import Any

from typing_extensions import Protocol

from ..aio_trampoline import Done, Trampoline
from ..curry import curry
from ..either import Either, Left, Right
from ..immutable import Immutable
from .effect import Effect, get_environment


class Files(Immutable):
    """
    Module that enables reading and writing from files
    """
    def read(self, path: str) -> Effect[Any, OSError, str]:
        """
        get an :class:`Effect` that reads the content of a file as a str

        :example:
        >>> Files().read('foo.txt').run(None)
        'contents of foo.txt'

        :param path: path to file
        :return: :class:`Effect` that reads file located at `path`
        """
        async def run_e(_) -> Trampoline[Either[OSError, str]]:
            try:
                with open(path) as f:
                    contents = f.read()
                return Done(Right(contents))
            except OSError as e:
                return Done(Left(e))

        return Effect(run_e)

    def read_bytes(self, path: str) -> Effect[Any, OSError, bytes]:
        """
        get an :class:`Effect` that reads the content of a file as bytes

        :example:
        >>> Files().read_bytes('foo.txt').run(None)
        b'contents of foo.txt'

        :param path: path to file
        :return: :class:`Effect` that reads file located at `path`
        """
        async def run_e(_) -> Trampoline[Either[OSError, bytes]]:
            try:
                with open(path, 'b') as f:
                    contents = f.read()
                return Done(Right(contents))
            except OSError as e:
                return Done(Left(e))

        return Effect(run_e)

    def write(self, path: str, content: str) -> Effect[Any, OSError, None]:
        """
        Get an :class:`Effect` that writes to a file

        :example:
        >>> files = Files()
        >>> files\\
        ...     .write('foo.txt', 'contents')\\
        ...     .discard_and_then(files.read('foo.txt'))\\
        ...     .run(None)
        'contents'

        :param path: the path of the file to be written
        :param: content the content to write
        :return: :class:`Effect` that that writes `content` to file at `path`
        """
        async def run_e(_) -> Trampoline[Either[OSError, None]]:
            try:
                with open(path, 'w') as f:
                    f.write(content)
                return Done(Right(None))
            except OSError as e:
                return Done(Left(e))

        return Effect(run_e)

    def write_bytes(self, path: str,
                    content: bytes) -> Effect[Any, OSError, None]:
        """
        Get an :class:`Effect` that writes to a file

        :example:
        >>> files = Files()
        >>> files\\
        ...     .write_bytes('foo.txt', b'contents')\\
        ...     .discard_and_then(files.read('foo.txt'))\\
        ...     .run(None)
        'contents'

        :param path: the path of the file to be written
        :param: content the content to write
        :return: :class:`Effect` that that writes `content` to file at `path`
        """
        async def run_e(_) -> Trampoline[Either[OSError, None]]:
            try:
                with open(path, 'wb') as f:
                    f.write(content)
                return Done(Right(None))
            except OSError as e:
                return Done(Left(e))

        return Effect(run_e)

    def append(self, path: str, content: str) -> Effect[Any, OSError, None]:
        """
        Get an :class:`Effect` that appends to a file

        :example:
        >>> files = Files()
        >>> files\\
        ...     .append('foo.txt', 'contents')\\
        ...     .discard_and_then(files.read('foo.txt'))\\
        ...     .run(None)
        'contents'

        :param path: the path of the file to be written
        :param: content the content to append
        :return: :class:`Effect` that that appends `content` to file at `path`
        """
        async def run_e(_) -> Trampoline[Either[OSError, None]]:
            try:
                with open(path, 'a+') as f:
                    f.write(content)
                return Done(Right(None))
            except OSError as e:
                return Done(Left(e))

        return Effect(run_e)

    def append_bytes(self, path: str,
                     content: bytes) -> Effect[Any, OSError, None]:
        """
        Get an :class:`Effect` that appends to a file

        :example:
        >>> files = Files()
        >>> files\\
        ...     .append_bytes('foo.txt', b'contents')\\
        ...     .discard_and_then(files.read('foo.txt'))\\
        ...     .run(None)
        'contents

        :param path: the path of the file to be written
        :param: content the content to append
        :return: :class:`Effect` that that appends `content` to file at `path`
        """
        async def run_e(_) -> Trampoline[Either[OSError, None]]:
            try:
                with open(path, 'ab+') as f:
                    f.write(content)
                return Done(Right(None))
            except OSError as e:
                return Done(Left(e))

        return Effect(run_e)


class HasFiles(Protocol):
    """
    Module provider that provides the files module

    :attribute files: The :class:`Files` instance
    """
    files: Files


def read(path: str) -> Effect[HasFiles, OSError, str]:
    """
    get an :class:`Effect` that reads the content of a file as a str

    :example:
    >>> class Env:
    ...     files = Files()
    >>> read('foo.txt').run(Env())
    'contents of foo.txt'

    :param path: path to file
    :return: :class:`Effect` that reads file located at `path`
    """
    return get_environment().and_then(lambda env: env.files.read(path))


@curry
def write(path: str, content: str) -> Effect[HasFiles, OSError, None]:
    """
    Get an :class:`Effect` that writes to a file

    :example:
    >>> class Env:
    ...     files = Files()
    >>> write('foo.txt')('contents')\\
    ...     .discard_and_then(read('foo.txt'))\\
    ...     .run(Env())
    'content of foo.txt'

    :param path: the path of the file to be written
    :param: content the content to write
    :return: :class:`Effect` that that writes `content` to file at `path`
    """
    return get_environment(
    ).and_then(lambda env: env.files.write(path, content))


def read_bytes(path: str) -> Effect[HasFiles, OSError, bytes]:
    """
    get an :class:`Effect` that reads the content of a file as bytes

    :example:
    >>> class Env:
    ...     files = Files()
    >>> read_bytes('foo.txt').run(Env())
    b'contents of foo.txt'

    :param path: path to file
    :return: :class:`Effect` that reads file located at `path`
    """
    return get_environment().and_then(lambda env: env.files.read_bytes(path))


@curry
def write_bytes(path: str, content: bytes) -> Effect[HasFiles, OSError, None]:
    """
    Get an :class:`Effect` that writes to a file

    :example:
    >>> class Env:
    ...     files = Files()
    >>> write_bytes('foo.txt')(b'content of foo.txt')\\
    ...     .discard_and_then(read('foo.txt'))\\
    ...     .run(Env())
    'content of foo.txt'

    :param path: the path of the file to be written
    :param: content the content to write
    :return: :class:`Effect` that that writes `content` to file at `path`
    """
    return get_environment(
    ).and_then(lambda env: env.files.write_bytes(path, content))


@curry
def append(path: str, content: str) -> Effect[HasFiles, OSError, None]:
    """
    Get an :class:`Effect` that appends to a file

    :example:
    >>> class Env:
    ...     files = Files()
    >>> append('foo.txt')('content of foo.txt')\\
    ...     .discard_and_then(read('foo.txt'))\\
    ...     .run(Env())
    'content of foo.txt'

    :param path: the path of the file to be written
    :param: content the content to append
    :return: :class:`Effect` that that appends `content` to file at `path`
    """
    return get_environment(
    ).and_then(lambda env: env.files.append(path, content))


@curry
def append_bytes(path: str, content: bytes) -> Effect[HasFiles, OSError, None]:
    """
    Get an :class:`Effect` that appends to a file

    :example:
    >>> class Env:
    ...     files = Files()
    >>> append_bytes('foo.txt')(b'content of foo.txt')\\
    ...     .discard_and_then(read('foo.txt'))\\
    ...     .run(Env())
    'content of foo.txt'

    :param path: the path of the file to be written
    :param: content the content to append
    :return: :class:`Effect` that that appends `content` to file at `path`
    """
    return get_environment(
    ).and_then(lambda env: env.files.append_bytes(path, content))
