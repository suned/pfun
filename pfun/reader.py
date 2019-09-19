from functools import wraps
from typing import Generic, TypeVar, Callable, Iterable, cast

from .immutable import Immutable
from .curry import curry
from .trampoline import Trampoline, Done, Call
from .monad import Monad, map_m_, sequence_, filter_m_
from .monadic import monadic

Context = TypeVar('Context')
Result_ = TypeVar('Result_')
Next = TypeVar('Next')

A = TypeVar('A')
B = TypeVar('B')


class Reader(Immutable, Generic[Context, Result_], Monad):
    """
    Class that represents a computation that is not yet completed, but
    will complete once given an object of type ``Context``

    """

    f: Callable[[Context], Trampoline[Result_]]

    def and_then(
        self: 'Reader[Context, Result_]',
        f: 'Callable[[Result_], Reader[Context, Next]]'
    ) -> 'Reader[Context, Next]':
        """
        Compose ``f`` with the function wrapped by this
        :class:`Reader` instance

        :example:
        >>> ask().and_then(
        ...     lambda context: value(f'context: {context}')
        ... ).run([])
        'context: []'

        :param f: Function to compose with this this :class:`Reader`
        :return: Composed :class:`Reader`
        """
        return Reader(
            lambda a: Call(
                lambda: self.f(a).and_then(  # type: ignore
                    lambda v: Call(lambda: f(v).f(a))  # type: ignore
                )
            )
        )

    def map(self, f: Callable[[Result_], B]) -> 'Reader[Context, B]':
        """
        Apply ``f`` to the result of this :class:`Reader`

        :example:
        >>> value(1).map(str).run(...)
        '1'

        :param f: Function to apply
        :return: :class:`Reader` that returns the result of
                 applying ``f`` to its result
        """
        return Reader(
            lambda a: self.f(a).and_then(lambda r: Done(f(r)))  # type: ignore
        )

    def run(self, c: Context) -> Result_:
        """
        Apply this :class:`Reader` to the context ``c``

        :example:
        >>> value(1).run(...)
        1

        :param c: The context to passed to the
                  function wrapped by this :class:`Reader`
        :return: The result of this :class:`Reader`
        """
        return self.f(c).run()  # type: ignore

    __call__ = run


def value(v: Result_) -> Reader[Context, Result_]:
    """
    Make a ``Reader`` that will produce ``v`` no matter the context

    :example:
    >>> value(1).run(None)
    1

    :param v: the value to put in a :class:`Reader` instance
    :return: :class:`Reader` that returns ``v`` when given any context
    """
    return Reader(lambda _: Done(v))


def ask() -> Reader[Context, Context]:
    return Reader(lambda c: Done(c))


def reader(f: Callable[..., B]) -> Callable[..., Reader[Context, B]]:
    """
    Wrap any function in a :class:`Reader` context.
    Useful for making non-monadic
    functions monadic. Can also be used as a decorator

    :example:
    >>> to_int = reader(int)
    >>> to_int('1').and_then(lambda i: i + 1).run(...)
    2

    :param f: Function to wrap
    :return: Wrapped function
    """
    @wraps(f)
    def dec(*args, **kwargs):
        result = f(*args, **kwargs)
        return value(result)

    return dec


@curry
def map_m(f: Callable[[A], Reader[Context, B]],
          iterable: Iterable[A]) -> Reader[Context, Iterable[B]]:
    return cast(Reader[Context, Iterable[B]], map_m_(value, f, iterable))


def sequence(iterable: Iterable[Reader[Context, B]]
             ) -> Reader[Context, Iterable[B]]:
    return cast(Reader[Context, Iterable[B]], sequence_(value, iterable))


@curry
def filter_m(f: Callable[[A], Reader[Context, bool]],
             iterable: Iterable[A]) -> Reader[Context, Iterable[A]]:
    return cast(Reader[Context, Iterable[A]], filter_m_(value, f, iterable))


def do(f):
    return monadic(value, f)


__all__ = ['Reader', 'reader', 'value', 'map_m', 'sequence', 'filter_m']
