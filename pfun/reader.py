from functools import wraps
from typing import Any, Callable, Generator, Generic, Iterable, TypeVar, cast

from .curry import curry
from .immutable import Immutable
from .monad import Monad, filter_m_, map_m_, sequence_
from .trampoline import Call, Done, Trampoline
from .with_effect import with_effect_

Context = TypeVar('Context')
Result_ = TypeVar('Result_')
Next = TypeVar('Next')

A = TypeVar('A')
B = TypeVar('B')


class Reader(Immutable, Generic[Context, Result_], Monad):
    """
    Represents a computation that is not yet completed, but
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
    """
    Make a :class:`Reader` that just returns the context.

    :return: :class:`Reader` that will return the context when run
    """
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
    """
    Map each in element in ``iterable`` to
    a :class:`Reader` by applying ``f``,
    combine the elements by ``and_then``
    from left to right and collect the results

    :example:
    >>> map_m(value, range(3)).run(...)
    (0, 1, 2)

    :param f: Function to map over ``iterable``
    :param iterable: Iterable to map ``f`` over
    :return: ``f`` mapped over ``iterable`` and combined from left to right.
    """
    return cast(Reader[Context, Iterable[B]], map_m_(value, f, iterable))


def sequence(iterable: Iterable[Reader[Context, B]]
             ) -> Reader[Context, Iterable[B]]:
    """
    Evaluate each :class:`Reader` in `iterable` from left to right
    and collect the results

    :example:
    >>> sequence([value(v) for v in range(3)]).run(...)
    (0, 1, 2)

    :param iterable: The iterable to collect results from
    :returns: :class:`Reader` of collected results
    """
    return cast(Reader[Context, Iterable[B]], sequence_(value, iterable))


@curry
def filter_m(f: Callable[[A], Reader[Context, bool]],
             iterable: Iterable[A]) -> Reader[Context, Iterable[A]]:
    """
    Map each element in ``iterable`` by applying ``f``,
    filter the results by the value returned by ``f``
    and combine from left to right.

    :example:
    >>> filter_m(lambda v: value(v % 2 == 0), range(3)).run(...)
    (0, 2)

    :param f: Function to map ``iterable`` by
    :param iterable: Iterable to map by ``f``
    :return: `iterable` mapped and filtered by `f`
    """
    return cast(Reader[Context, Iterable[A]], filter_m_(value, f, iterable))


Readers = Generator[Reader[Context, Result_], Result_, B]


def with_effect(f: Callable[..., Readers[Context, Any, B]]
                ) -> Callable[..., Reader[Context, B]]:
    """
    Decorator for functions that
    return a generator of readers and a final result.
    Iteraters over the yielded readers and sends back the
    unwrapped values using "and_then"

    :example:
    >>> @with_effect
    ... def f() -> Readers[Any, int, int]:
    ...     a = yield value(2)
    ...     b = yield value(2)
    ...     return a + b
    >>> f().run()
    4

    :param f: generator function to decorate
    :return: `f` decorated such that generated :class:`Maybe` \
        will be chained together with `and_then`
    """
    return with_effect_(value, f)


__all__ = [
    'Reader',
    'reader',
    'value',
    'map_m',
    'sequence',
    'filter_m',
    'ask',
    'with_effect',
    'Readers'
]
