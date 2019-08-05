from pfun import Just, Nothing, List, reader, state, Dict, cont, writer
from hypothesis.strategies import (
    integers,
    booleans,
    text,
    one_of,
    floats,
    builds,
    just,
    lists as lists_,
    dictionaries,
    tuples,
    none
)

from pfun.result import Ok, Error


def _everything(allow_nan=False):
    return integers(), booleans(), text(), floats(allow_nan=allow_nan)


def anything(allow_nan=False):
    return one_of(*_everything(allow_nan))


def unaries(return_strategy=anything()):
    def _(a):
        return lambda _: a
    return builds(_, return_strategy)


def maybes(value_strategy=anything()):
    justs = builds(Just, value_strategy)
    nothings = just(Nothing())
    return one_of(justs, nothings)


def results(value_strategy=anything()):
    oks = builds(Ok, value_strategy)
    errors = just(Error(Exception()))
    return one_of(oks, errors)


def lists(element_strategies=_everything(allow_nan=False), min_size=0):
    return builds(
        List,
        one_of(*(lists_(strategy, min_size=min_size) for strategy in element_strategies))
    )


def readers(value_strategy=anything()):
    return builds(reader.value, value_strategy)


def states(value_strategy=anything()):
    return builds(state.value, value_strategy)


def dicts(keys=text(), values=anything(), min_size=0, max_size=None):
    return builds(Dict, dictionaries(keys, values, min_size=min_size, max_size=max_size))


def conts(value_strategy=anything()):
    return builds(cont.value, value_strategy)


def writers(value_strategy=anything(), monoid=lists()):
    return builds(writer.value, value_strategy, monoid)


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
