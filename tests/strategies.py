from string import printable

from hypothesis.strategies import (booleans, builds, composite, dictionaries,
                                   floats, integers, just)
from hypothesis.strategies import lists as lists_
from hypothesis.strategies import none, one_of, recursive, text, tuples
from pfun import Dict, List, aio_trampoline, effect, maybe, trampoline
from pfun.either import Left, Right


def _everything(allow_nan=False):
    return integers(), booleans(), text(), floats(allow_nan=allow_nan)


def anything(allow_nan=False):
    return one_of(*_everything(allow_nan))


@composite
def unaries(draw, return_strategy=anything()):
    a = draw(return_strategy)
    return lambda _: a


def maybes(value_strategy=anything()):
    justs = builds(maybe.Just, value_strategy)
    nothings = just(maybe.Nothing())
    return one_of(justs, nothings)


def rights(value_strategy=anything()):
    return builds(Right, value_strategy)


def lefts(value_strategy=anything()):
    return builds(Left, value_strategy)


def eithers(value_strategy=anything()):
    return one_of(lefts(), rights())


def nullaries(value_strategy=anything()):
    def f(v):
        return lambda: v

    return builds(f, value_strategy)


def trampolines(value_strategy=anything()):
    dones = builds(trampoline.Done, value_strategy)

    @composite
    def call(draw):
        t = draw(trampolines(value_strategy))
        return trampoline.Call(lambda: t)

    @composite
    def and_then(draw):
        t = draw(trampolines(value_strategy))
        cont = lambda _: t
        return trampoline.AndThen(draw(trampolines(value_strategy)), cont)

    return one_of(dones, call(), and_then())


def aio_trampolines(value_strategy=anything()):
    dones = builds(aio_trampoline.Done, value_strategy)

    @composite
    def call(draw):
        t = draw(aio_trampolines(value_strategy))

        async def f():
            return t

        return aio_trampoline.Call(f)

    @composite
    def and_then(draw):
        t = draw(aio_trampolines(value_strategy))
        cont = lambda _: t
        return aio_trampoline.AndThen(
            draw(aio_trampolines(value_strategy)), cont
        )

    return one_of(dones, call(), and_then())


def lists(element_strategies=_everything(allow_nan=False), min_size=0):
    return builds(
        List,
        one_of(
            *(
                lists_(strategy, min_size=min_size)
                for strategy in element_strategies
            )
        )
    )


def dicts(keys=text(), values=anything(), min_size=0, max_size=None):
    return builds(
        Dict, dictionaries(keys, values, min_size=min_size, max_size=max_size)
    )


def monoids():
    return one_of(
        lists_(anything()),
        lists(),
        tuples(),
        integers(),
        none(),
        text(),
        just(...)
    )


def effects(value_strategy=anything(), include_errors=False):
    def extend(children):
        maps = children.flatmap(lambda e: unaries().map(lambda f: e.map(f)))
        and_then = children.flatmap(
            lambda e: unaries(children).map(lambda f: e.and_then(f))
        )
        discard_and_then = children.flatmap(
            lambda e: children.map(lambda e2: e.discard_and_then(e2))
        )
        either = children.map(lambda e: e.either())
        recover = children.flatmap(
            lambda e: children.map(lambda e2: e.recover(e2))
        )
        memoize = children.map(lambda e: e.memoize())
        ensure = children.flatmap(
            lambda e: children.map(lambda e2: e.ensure(e2))
        )
        with_repr = children.flatmap(
            lambda e: text(printable).map(lambda s: e.with_repr(s))
        )
        sequence = lists_(children, max_size=10).map(effect.sequence)
        sequence_async = lists_(children,
                                max_size=10).map(effect.sequence_async)
        lift = unaries(value_strategy).flatmap(
            lambda f: children.map(lambda e: effect.lift(f)(e))
        )
        lift_io_bound = unaries(value_strategy).flatmap(
            lambda f: children.map(lambda e: effect.lift_io_bound(f)(e))
        )
        lift_cpu_bound = unaries(value_strategy).flatmap(
            lambda f: children.map(lambda e: effect.lift_cpu_bound(f)(e))
        )
        combine = unaries(value_strategy).flatmap(
            lambda f: children.map(lambda e: effect.combine(e)(f))
        )
        combine_io_bound = unaries(value_strategy).flatmap(
            lambda f: children.map(lambda e: effect.combine_io_bound(e)(f))
        )
        combine_cpu_bound = unaries(value_strategy).flatmap(
            lambda f: children.map(lambda e: effect.combine_cpu_bound(e)(f))
        )

        return one_of(
            maps,
            and_then,
            discard_and_then,
            either,
            recover,
            memoize,
            ensure,
            with_repr,
            sequence,
            sequence_async,
            lift,
            lift_io_bound,
            lift_cpu_bound,
            combine,
            combine_io_bound,
            combine_cpu_bound
        )

    success = builds(effect.success, value_strategy)
    depends = builds(effect.depend)
    errors = builds(effect.error, value_strategy)
    from_callable = unaries(rights(value_strategy)).map(effect.from_callable)
    from_io_bound_callable = unaries(rights(value_strategy)
                                     ).map(effect.from_io_bound_callable)
    from_cpu_bound_callable = unaries(rights(value_strategy)
                                      ).map(effect.from_cpu_bound_callable)
    catch = unaries(value_strategy).flatmap(
        lambda f: value_strategy.map(lambda a: effect.catch(Exception)(f)(a))
    )
    catch_io_bound = unaries(value_strategy).flatmap(
        lambda f: value_strategy.
        map(lambda a: effect.catch_io_bound(Exception)(f)(a))
    )
    catch_cpu_bound = unaries(value_strategy).flatmap(
        lambda f: value_strategy.
        map(lambda a: effect.catch_cpu_bound(Exception)(f)(a))
    )

    base = ( success
           | from_callable
           | from_io_bound_callable
           | from_cpu_bound_callable
           | depends
           | catch
           | catch_io_bound
           | catch_cpu_bound )

    if include_errors:
        base = base | errors

    return recursive(base, extend, max_leaves=10)
