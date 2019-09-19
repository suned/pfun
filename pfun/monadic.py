from functools import wraps
from pfun.monad import Monad
from pfun.trampoline import Call, Done
from pfun.curry import curry
from typing import Generator, TypeVar, Callable, Any

M = TypeVar('M', bound=Monad)


@curry
def monadic(
    value: Callable[[Any], M], f: Callable[..., Generator[M, Any, Any]]
) -> Callable[..., M]:
    @wraps(f)
    def decorator(*args, **kwargs):
        g = f(*args, **kwargs)

        def cont(v) -> M:
            try:
                # TODO trampoline. BUT HOW??
                return g.send(v).and_then(cont)
            except StopIteration as e:
                return value(e.value)

        m = next(g)
        return m.and_then(cont)

    return decorator
