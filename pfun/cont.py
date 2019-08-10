from typing import Generic, Callable, TypeVar, Any

from pfun import compose
from .immutable import Immutable

A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')
D = TypeVar('D')


class Cont(Generic[A, B], Immutable):
    """
    Type that represents a function in continuation passing style.
    """
    f: Callable[[Callable[[A], B]], B]

    def and_then(self, f: 'Callable[[B], Cont[C, D]]') -> 'Cont[C, D]':
        """
        Chain together functions in continuation passing style

        :example:
        >>> value(1).and_then(lambda i: value(i + 1)).run(identity)
        2

        :param f: Function in continuation passing style to chain with
        the result of this function
        :return:
        """
        return Cont(lambda c: self.run(lambda a: f(a).run(c)))  # type: ignore

    def run(self, f: Callable[[A], B]) -> B:
        """
        Run the wrapped function in continuation passing style by passing the
        result to ``f``

        :example:
        >>> from pfun import identity
        >>> value(1).run(identity)
        1

        :param f: The function to pass the result of the wrapped function to
        :return: the result of passing the return value of the wrapped function to ``f``
        """
        return self.f(f)  # type: ignore

    __call__ = run

    def map(self, f: Callable[[B], C]) -> 'Cont[B, C]':
        return Cont(lambda c: self.run(compose(c, f)))  # type: ignore


def value(a: A) -> Cont[A, B]:
    """
    Wrap a constant value in a :class:`Cont` context

    :example:
    >>> from pfun import identity
    >>> value(1).run(identity)
    1

    :param a: Constant value to wrap
    :return: :class:`Cont` wrapping the value
    """
    return Cont(lambda cont: cont(a))

