from hypothesis import given, assume
from hypothesis.strategies import builds

from pfun import writer
from tests.monad_test import MonadTest
from tests.strategies import anything, unaries, writers, monoids, lists


def tuple_identity(a, m):
    return a, m


def tuple_compose(f, g):
    return lambda a, m: f(*g(a, m))


def monoidal_dyads(value_strategy=anything(), monoids=lists()):
    def _(a, m):
        return lambda a_, m_: (a, m)

    return builds(_, value_strategy, monoids)


class TestWriter(MonadTest):
    @given(anything(), monoids())
    def test_right_identity_law(self, value, monoid):
        assert (writer.value(value,
                             monoid).and_then(writer.value) == writer.value(
                                 value, monoid))

    @given(unaries(writers()), anything())
    def test_left_identity_law(self, f, value):
        assert writer.value(value).and_then(f) == f(value)

    @given(writers(), unaries(writers()), unaries(writers()))
    def test_associativity_law(self, w, f, g):
        assert w.and_then(f).and_then(g) == w.and_then(
            lambda x: f(x).and_then(g))

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
        assert writer.value(value).map(tuple_identity) == writer.value(value)

    @given(monoidal_dyads(), monoidal_dyads(), anything())
    def test_composition_law(self, f, g, value):
        h = tuple_compose(f, g)
        assert writer.value(value).map(h) == writer.value(value).map(g).map(f)

    @given(monoids())
    def test_tell(self, monoid):
        assert writer.tell(monoid) == writer.value(None, monoid)
