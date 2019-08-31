from hypothesis import given, assume

from pfun import cont, identity, compose
from tests.monad_test import MonadTest
from tests.strategies import anything, unaries, conts


class TestCont(MonadTest):
    @given(anything())
    def test_right_identity_law(self, value):
        assert (cont.value(value).and_then(
            cont.value).run(identity) == cont.value(value).run(identity))

    @given(unaries(conts()), anything())
    def test_left_identity_law(self, f, value):
        assert (cont.value(value).and_then(f).run(identity) == f(value).run(
            identity))

    @given(conts(), unaries(conts()), unaries(conts()))
    def test_associativity_law(self, c, f, g):
        assert (c.and_then(f).and_then(g).run(identity) == c.and_then(
            lambda x: f(x).and_then(g)).run(identity))

    @given(anything())
    def test_equality(self, value):
        assert cont.value(value).run(identity) == cont.value(value).run(
            identity)

    @given(anything(), anything())
    def test_inequality(self, first, second):
        assume(first != second)
        assert cont.value(first).run(identity) != cont.value(second).run(
            identity)

    @given(anything())
    def test_identity_law(self, value):
        assert (cont.value(value).map(identity).run(identity) == cont.value(
            value).run(identity))

    @given(unaries(), unaries(), anything())
    def test_composition_law(self, f, g, value):
        h = compose(f, g)
        assert (cont.value(value).map(h).run(identity) == cont.value(
            value).map(g).map(f).run(identity))
