from hypothesis import given

from pfun import pipe
from tests.strategies import unaries, anything


@given(unaries(), unaries(), anything())
def test_pipe(f, g, a):
    assert a >> pipe(f).and_then(g) == g(f(a))
