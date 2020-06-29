from functools import wraps
from typing import Any, Callable, Generator, TypeVar

from pfun.curry import curry
from pfun.monad import Monad

M = TypeVar('M', bound=Monad)


@curry
def with_effect_(
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

        try:
            m = next(g)
            return m.and_then(cont)
        except StopIteration as e:
            return value(e.value)

    return decorator


@curry
def with_effect_eager(
    value: Callable[[Any], M], f: Callable[..., Generator[M, Any, Any]]
) -> Callable[..., M]:
    """
    DANGER! This approach only works for monads that bind functions
    eagerly such as Maybe, Either, Writer and List
    """
    @wraps(f)
    def decorator(*args, **kwargs):
        g = f(*args, **kwargs)
        m = next(g)
        try:
            while True:
                m = m.and_then(lambda v: g.send(v))
        except StopIteration as e:
            return value(e.value)

    return decorator


@curry
def with_effect_tail_rec(
    value: Callable[[Any], M],
    f: Callable[..., Generator[M, Any, Any]],
    tail_rec: Callable[[Callable[[Any], Any], Any], Any] = None
) -> Callable[..., M]:

    from .either import Left, Right

    @wraps(f)
    def decorator(*args, **kwargs):
        g = f(*args, **kwargs)

        def cont(v) -> M:
            try:
                return g.send(v).map(Left)
            except StopIteration as e:
                return value(Right(e.value))

        try:
            m = next(g)
            return m.and_then(lambda v: tail_rec(cont, v))
        except StopIteration as e:
            return value(e.value)

    return decorator
