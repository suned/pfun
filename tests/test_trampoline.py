from hypothesis import given, assume
from pfun.trampoline import Done
from pfun import identity, compose

from .strategies import trampolines, unaries, anything
from .monad_test import MonadTest


class TestTrampoline(MonadTest):
    @given(trampolines())
    def test_right_identity_law(self, trampoline):
        assert trampoline.and_then(Done).run() == trampoline.run()

    @given(anything(), unaries(trampolines()))
    def test_left_identity_law(self, value, f):
        assert Done(value).and_then(f).run() == f(value).run()

    @given(trampolines(), unaries(trampolines()), unaries(trampolines()))
    def test_associativity_law(self, trampoline, f, g):
        assert trampoline.and_then(f).and_then(g).run(
        ) == trampoline.and_then(lambda x: f(x).and_then(g)).run()

    @given(anything())
    def test_equality(self, value):
        assert Done(value) == Done(value)

    @given(anything(), anything())
    def test_inequality(self, first, second):
        assume(first != second)
        assert Done(first) != Done(second)

    @given(anything())
    def test_identity_law(self, value):
        assert Done(value).map(identity).run() == Done(value).run()

    @given(unaries(), unaries(), anything())
    def test_composition_law(self, f, g, value):
        h = compose(f, g)
        assert Done(value).map(g).map(f).run() == Done(value).map(h).run()
