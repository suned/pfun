from functools import wraps
from typing import Generic, TypeVar, Callable

from .util import identity
from .immutable import Immutable

Context = TypeVar('Context')
Result_ = TypeVar('Result_')
Next = TypeVar('Next')

A = TypeVar('A')
B = TypeVar('B')


class Reader(Generic[Context, Result_], Immutable):
    """
    Class that represents a computation that is not yet completed, but
    will complete once given an object of type ``Context``

    """
    def __init__(self, f: Callable[[Context], Result_]):
        """
        Create a :class:`Reader` that wraps the function f which will produce
        a value of type ``Result`` when given a value of type ``Context``

        :example:
        >>> Reader(lambda l: l + ['second value']).run(['first value'])
        ['first value', 'second value']

        :param f: function to wrap
        """
        self.f = f

    def and_then(self, f: 'Callable[[Result_], Reader[Context, Next]]') -> 'Reader[Context, Next]':
        """
        Compose ``f`` with the function wrapped by this :class:`Reader` instance

        :example:
        >>> ask().and_then(
        ...     lambda context: value(f'context: {context}')
        ... ).run([])
        'context: []'

        :param f: Function to compose with this this :class:`Reader`
        :return: Composed :class:`Reader`
        """
        return Reader(lambda a: f(self.f(a)).f(a))

    def map(self, f: Callable[[Result_], B]) -> 'Reader[Context, B]':
        """
        Apply ``f`` to the result of this :class:`Reader`

        :example:
        >>> value(1).map(str).run(...)
        '1'

        :param f: Function to apply
        :return: :class:`Reader` that returns the result of applying ``f`` to its result
        """
        return Reader(lambda a: f(self.f(a)))

    def run(self, c: Context) -> Result_:
        """
        Apply this :class:`Reader` to the context ``c``

        :example:
        >>> value(1).run(...)
        1

        :param c: The context to passed to the function wrapped by this :class:`Reader`
        :return: The result of this :class:`Reader`
        """
        return self.f(c)

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
    Wrap any function in a :class:`Reader` context. Useful for making non-monadic
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
