from functools import wraps
from pfun.monad import Monad
from pfun.trampoline import Trampoline
from pfun.either import Left, Right
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
                return g.send(v).and_then(cont)
            except StopIteration as e:
                return value(e.value)

        m = next(g)
        return m.and_then(cont)

    return decorator


@curry
def monadic_tail_rec(
    value: Callable[[Any], M],
    f: Callable[..., Generator[M, Any, Any]],
    tail_rec: Callable[[Callable[[Any], Any], Any], Trampoline] = None
) -> Callable[..., M]:
    @wraps(f)
    def decorator(*args, **kwargs):
        g = f(*args, **kwargs)

        def cont(v) -> M:
            try:
                return g.send(v).map(Left)
            except StopIteration as e:
                return value(Right(e.value))

        m = next(g)
        return m.and_then(lambda v: tail_rec(cont, v).run())

    return decorator
