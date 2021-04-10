from string import printable

from hypothesis import given
from hypothesis.strategies import text

from pfun import functions
from pfun.hypothesis_strategies import anything, dicts, lists, unaries


@given(anything(allow_nan=False))
def test_identity(a):
    assert functions.identity(a) == a


@given(unaries(anything()), unaries(anything()), anything())
def test_compose(f, g, arg):
    h = functions.compose(f, g)
    assert h(arg) == f(g(arg))


@given(anything(), lists(anything()), dicts(text(printable), anything()))
def test_always(value, args, kwargs):
    f = functions.always(value)
    assert f(*args, **kwargs) == value
