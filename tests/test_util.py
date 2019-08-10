from hypothesis import given

from pfun import util
from tests.strategies import anything, unaries, lists, dicts


@given(anything(allow_nan=False))
def test_identity(a):
    assert util.identity(a) == a


@given(unaries(), unaries(), anything())
def test_compose(f, g, arg):
    h = util.compose(f, g)
    assert h(arg) == f(g(arg))


@given(anything(), lists(), dicts())
def test_always(value, args, kwargs):
    f = util.always(value)
    assert f(*args, **kwargs) == value
