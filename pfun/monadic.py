from functools import wraps
from pfun.monad import Monad
from pfun.curry import curry
from typing import Generator, TypeVar, Callable, Any

M = TypeVar('M', bound=Monad)


@curry
def monadic(
    value: Callable[[Any], M], f: Callable[..., Generator[M, Any, Any]]
) -> Callable[..., M]:
    @wraps(f)
    def decorator(*args, **kwargs):
        g = f()
        m = next(g)
        while True:
            try:
                m = m.and_then(lambda v: g.send(v))
                if not m:
                    # special case for monads that
                    # don't actually call the 'and_then'
                    # function argument such as maybe.Nothing etc
                    return m
            except StopIteration as e:
                return value(e.value)

    return decorator
