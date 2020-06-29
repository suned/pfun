import functools
import inspect
from typing import Callable

from .immutable import Immutable


class Curry(Immutable):
    f: Callable

    def __repr__(self):
        return repr(self.f)

    def __call__(self, *args, **kwargs):
        signature = inspect.signature(self.f)
        bound = signature.bind_partial(*args, **kwargs)
        bound.apply_defaults()
        arg_names = {a for a in bound.arguments.keys()}
        parameters = {p for p in signature.parameters.keys()}
        if parameters - arg_names == set():
            return self.f(*args, **kwargs)
        partial = functools.partial(self.f, *args, **kwargs)
        return Curry(partial)


def curry(f: Callable) -> Callable:
    """
    Get a version of ``f`` that can be partially applied

    :example:
    >>> f = lambda a, b: a + b
    >>> f_curried = curry(f)
    >>> f_curried(1)
    functools.partial(<function <lambda> at 0x1051f0950>, a=1)
    >>> f_curried(1)(1)
    2

    :param f: The function to curry
    :return: Curried version of ``f``
    """
    @functools.wraps(f)
    def decorator(*args, **kwargs):
        return Curry(f)(*args, **kwargs)

    return decorator


__all__ = ['curry']
