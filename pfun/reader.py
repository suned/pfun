from functools import wraps
from typing import Generic, TypeVar, Callable

from .util import identity
from .immutable import Immutable

Context = TypeVar('Context')
Result_ = TypeVar('Result_')
Next = TypeVar('Next')

A = TypeVar('A')
B = TypeVar('B')


class Reader(Immutable, Generic[Context, Result_]):
    """
    Class that represents a computation that is not yet completed, but
    will complete once given an object of type ``Context``

    """

    f: Callable[[Context], Result_]

    def and_then(self, f: 'Callable[[Result_], Reader[Context, Next]]'
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
        return Reader(lambda a: f(self.f(a)).f(a))  # type: ignore

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
        return Reader(lambda a: f(self.f(a)))  # type: ignore

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
        return self.f(c)  # type: ignore

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
    return Reader(lambda _: v)


def ask() -> Reader[Context, Result_]:
    """
    Return the :class:`Reader` that simply returns the context it is given

    :example:
    >>> ask().run('context')
    'context'

    :return: :class:`Reader` that returns the context
    """
    return Reader(identity)  # type: ignore


def reader(f: Callable[[A], B]) -> Callable[[A], Reader[Context, B]]:
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


__all__ = ['Reader', 'reader', 'value', 'ask']
