from typing_extensions import Protocol

from .effect import Effect, Try, add_repr, catch, depend, io_bound
from .functions import curry
from .immutable import Immutable


class Files(Immutable):
    """
    Module that enables reading and writing from files
    """
    def read(self, path: str) -> Try[OSError, str]:
        """
        get an `Effect` that reads the content of a file as a str

        Example:
            >>> Files().read('foo.txt').run(None)
            'contents of foo.txt'

        Args:
            path: path to file
        Return:
            `Effect` that reads file located at `path`
        """
        @io_bound
        def f() -> str:
            with open(path) as f:
                return f.read()

        return catch(OSError)(f)()

    def read_bytes(self, path: str) -> Try[OSError, bytes]:
        """
        get an `Effect` that reads the content of a file as bytes

        Example:
            >>> Files().read_bytes('foo.txt').run(None)
            b'contents of foo.txt'

        Args:
            path: path to file
        Return:
            `Effect` that reads file located at `path`
        """
        @io_bound
        def f() -> bytes:
            with open(path, 'rb') as f:
                return f.read()

        return catch(OSError)(f)()

    def write(self, path: str, content: str) -> Try[OSError, None]:
        """
        Get an `Effect` that writes to a file

        Example:
            >>> files = Files()
            >>> files\\
            ...     .write('foo.txt', 'contents')\\
            ...     .discard_and_then(files.read('foo.txt'))\\
            ...     .run(None)
            'contents'

        Args:
            path: the path of the file to be written
            content the content to write
        Return:
            `Effect` that that writes `content` to file at `path`
        """
        @io_bound
        def f() -> None:
            with open(path, 'w') as f:
                f.write(content)

        return catch(OSError)(f)()

    def write_bytes(self, path: str, content: bytes) -> Try[OSError, None]:
        """
        Get an `Effect` that writes to a file

        Example:
            >>> files = Files()
            >>> files\\
            ...     .write_bytes('foo.txt', b'contents')\\
            ...     .discard_and_then(files.read('foo.txt'))\\
            ...     .run(None)
            'contents'

        Args:
            path: the path of the file to be written
            content the content to write
        Return:
            `Effect` that that writes `content` to file at `path`
        """
        @io_bound
        def f() -> None:
            with open(path, 'wb') as f:
                f.write(content)

        return catch(OSError)(f)()

    def append(self, path: str, content: str) -> Try[OSError, None]:
        """
        Get an `Effect` that appends to a file

        Example:
            >>> files = Files()
            >>> files\\
            ...     .append('foo.txt', 'contents')\\
            ...     .discard_and_then(files.read('foo.txt'))\\
            ...     .run(None)
            'contents'

        Args:
            path: the path of the file to be written
            content the content to append
        Return:
            `Effect` that that appends `content` to file at `path`
        """
        @io_bound
        def f() -> None:
            with open(path, 'a+') as f:
                f.write(content)

        return catch(OSError)(f)()

    def append_bytes(self, path: str, content: bytes) -> Try[OSError, None]:
        """
        Get an `Effect` that appends to a file

        Example:
            >>> files = Files()
            >>> files\\
            ...     .append_bytes('foo.txt', b'contents')\\
            ...     .discard_and_then(files.read('foo.txt'))\\
            ...     .run(None)
            'contents

        Args:
            path: the path of the file to be written
            content the content to append
        Return:
            `Effect` that that appends `content` to file at `path`
        """
        @io_bound
        def f() -> None:
            with open(path, 'ab+') as f:
                f.write(content)

        return catch(OSError)(f)()


class HasFiles(Protocol):
    """
    Module provider that provides the files module

    :attribute files: The `Files` instance
    """
    files: Files


@add_repr
def read(path: str) -> Effect[HasFiles, OSError, str]:
    """
    get an `Effect` that reads the content of a file as a str

    Example:
        >>> class Env:
        ...     files = Files()
        >>> read('foo.txt').run(Env())
        'contents of foo.txt'

    Args:
        path: path to file
    Return:
        `Effect` that reads file located at `path`
    """
    return depend(HasFiles).and_then(lambda env: env.files.read(path))


@curry
@add_repr
def write(path: str, content: str) -> Effect[HasFiles, OSError, None]:
    """
    Get an `Effect` that writes to a file

    Example:
        >>> class Env:
        ...     files = Files()
        >>> write('foo.txt')('contents')\\
        ...     .discard_and_then(read('foo.txt'))\\
        ...     .run(Env())
        'content of foo.txt'

    Args:
        path: the path of the file to be written
        content the content to write
    Return:
        `Effect` that that writes `content` to file at `path`
    """
    return depend(HasFiles
                  ).and_then(lambda env: env.files.write(path, content))


@add_repr
def read_bytes(path: str) -> Effect[HasFiles, OSError, bytes]:
    """
    get an `Effect` that reads the content of a file as bytes

    Example:
        >>> class Env:
        ...     files = Files()
        >>> read_bytes('foo.txt').run(Env())
        b'contents of foo.txt'

    Args:
        path: path to file
    Return:
        `Effect` that reads file located at `path`
    """
    return depend(HasFiles).and_then(lambda env: env.files.read_bytes(path))


@curry
@add_repr
def write_bytes(path: str, content: bytes) -> Effect[HasFiles, OSError, None]:
    """
    Get an `Effect` that writes to a file

    Example:
        >>> class Env:
        ...     files = Files()
        >>> write_bytes('foo.txt')(b'content of foo.txt')\\
        ...     .discard_and_then(read('foo.txt'))\\
        ...     .run(Env())
        'content of foo.txt'

    Args:
        path: the path of the file to be written
        content the content to write
    Return:
        `Effect` that that writes `content` to file at `path`
    """
    return depend(HasFiles
                  ).and_then(lambda env: env.files.write_bytes(path, content))


@curry
@add_repr
def append(path: str, content: str) -> Effect[HasFiles, OSError, None]:
    """
    Get an `Effect` that appends to a file

    Example:
        >>> class Env:
        ...     files = Files()
        >>> append('foo.txt')('content of foo.txt')\\
        ...     .discard_and_then(read('foo.txt'))\\
        ...     .run(Env())
        'content of foo.txt'

    Args:
        path: the path of the file to be written
        content the content to append
    Return:
        `Effect` that that appends `content` to file at `path`
    """
    return depend(HasFiles
                  ).and_then(lambda env: env.files.append(path, content))


@curry
@add_repr
def append_bytes(path: str, content: bytes) -> Effect[HasFiles, OSError, None]:
    """
    Get an `Effect` that appends to a file

    Example:
        >>> class Env:
        ...     files = Files()
        >>> append_bytes('foo.txt')(b'content of foo.txt')\\
        ...     .discard_and_then(read('foo.txt'))\\
        ...     .run(Env())
        'content of foo.txt'

    Args:
        path: the path of the file to be written
        content the content to append
    Return:
        `Effect` that that appends `content` to file at `path`
    """
    return depend(HasFiles).and_then(
        lambda env: env.files.append_bytes(path, content)
    )
