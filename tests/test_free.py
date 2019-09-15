from hypothesis import given, assume
from pfun.free import Done
from pfun import identity, compose

from .strategies import frees, unaries, anything
from .monad_test import MonadTest


class TestFree(MonadTest):
    @given(frees())
    def test_right_identity_law(self, free):
        assert free.and_then(Done) == free

    @given(anything(), unaries(frees()))
    def test_left_identity_law(self, value, f):
        assert Done(value).and_then(f) == f(value)

    @given(frees(), unaries(frees()), unaries(frees()))
    def test_associativity_law(self, free, f, g):
        assert free.and_then(f).and_then(g)  == free.and_then(lambda x: f(x).and_then(g))

    @given(anything())
    def test_equality(self, value):
        assert Done(value) == Done(value)

    @given(anything(), anything())
    def test_inequality(self, first, second):
        assume(first != second)
        assert Done(first) != Done(second)

    @given(anything())
    def test_identity_law(self, value):
        assert Done(value).map(identity) == Done(value)

    @given(unaries(), unaries(), anything())
    def test_composition_law(self, f, g, value):
        h = compose(f, g)
        assert Done(value).map(g).map(f) == Done(value).map(h)
