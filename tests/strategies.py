from pfun import Just, Nothing, List, reader
from hypothesis.strategies import (
    integers,
    booleans,
    text,
    one_of,
    floats,
    builds,
    just,
    lists as lists_
)


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


def lists(element_strategies=_everything(allow_nan=False)):
    return builds(
        lambda t: List(t),
        one_of(*(lists_(strategy) for strategy in element_strategies))
    )


def readers(value_strategy=anything()):
    return builds(reader.value, value_strategy)
