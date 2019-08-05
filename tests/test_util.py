from hypothesis import given
from hypothesis.strategies import integers, text

from pfun import util, curry
from tests.strategies import anything, unaries


@given(anything(allow_nan=False))
def test_identity(a):
    assert util.identity(a) == a


@given(unaries(), unaries(), anything())
def test_compose(f, g, arg):
    h = util.compose(f, g)
    assert h(arg) == f(g(arg))


@given(integers(), text())
def test_flip(i, s):
    is_int = util.flip(curry(isinstance))(int)
    assert is_int(i)
    assert not is_int(s)
