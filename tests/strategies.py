from hypothesis.strategies import (booleans, builds, composite, dictionaries,
                                   floats, integers, just)
from hypothesis.strategies import lists as lists_
from hypothesis.strategies import none, one_of, text, tuples

from pfun import Dict, List, aio_trampoline, effect, maybe, trampoline
from pfun.either import Left, Right


def _everything(allow_nan=False):
    return integers(), booleans(), text(), floats(allow_nan=allow_nan)


def anything(allow_nan=False):
    return one_of(*_everything(allow_nan))


def unaries(return_strategy=anything()):
    def _(a):
        return lambda _: a

    return builds(_, return_strategy)


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


def effects(value_strategy=anything()):
    return builds(effect.success, value_strategy)
