from hypothesis import given
from pfun import functions

from tests.strategies import anything, dicts, lists, unaries


@given(anything(allow_nan=False))
def test_identity(a):
    assert functions.identity(a) == a


@given(unaries(), unaries(), anything())
def test_compose(f, g, arg):
    h = functions.compose(f, g)
    assert h(arg) == f(g(arg))


@given(anything(), lists(), dicts())
def test_always(value, args, kwargs):
    f = functions.always(value)
    assert f(*args, **kwargs) == value
