from hypothesis import given, assume

from pfun import writer
from pfun import identity, compose
from tests.monad_test import MonadTest
from tests.strategies import anything, unaries, writers, monoids


class TestWriter(MonadTest):
    @given(anything(), monoids())
    def test_right_identity_law(self, value, monoid):
        assert (
            writer.value(value,
                         monoid).and_then(writer.value
                                          ) == writer.value(value, monoid)
        )

    @given(unaries(writers()), anything())
    def test_left_identity_law(self, f, value):
        assert writer.value(value).and_then(f) == f(value)

    @given(writers(), unaries(writers()), unaries(writers()))
    def test_associativity_law(self, w, f, g):
        assert w.and_then(f).and_then(g) == w.and_then(
            lambda x: f(x).and_then(g)
        )

    @given(anything(), monoids())
    def test_equality(self, value, monoid):
        assert writer.value(value, monoid) == writer.value(value, monoid)
        assert writer.value(value) != value

    @given(anything(), anything(), monoids())
    def test_inequality(self, first, second, monoid):
        assume(first != second)
        assert writer.value(first, monoid) != writer.value(second, monoid)

    @given(anything())
    def test_identity_law(self, value):
        assert writer.value(value).map(identity) == writer.value(value)

    @given(unaries(), unaries(), anything())
    def test_composition_law(self, f, g, value):
        h = compose(f, g)
        assert writer.value(value).map(h) == writer.value(value).map(g).map(f)

    @given(monoids())
    def test_tell(self, monoid):
        assert writer.tell(monoid) == writer.value(None, monoid)
