from hypothesis import assume, given

from pfun import compose, identity
from pfun.trampoline import Done, filter_m, map_m, sequence, with_effect

from .monad_test import MonadTest
from .strategies import anything, trampolines, unaries
from .utils import recursion_limit


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

    def test_with_effect(self):
        @with_effect
        def f():
            a = yield Done(2)
            b = yield Done(2)
            return a + b

        assert f().run() == 4

        @with_effect
        def test_stack_safety():
            for _ in range(500):
                yield Done(1)
            return None

        with recursion_limit(100):
            test_stack_safety().run()

    def test_sequence(self):
        assert sequence([Done(v) for v in range(3)]).run() == (0, 1, 2)

    def test_stack_safety(self):
        with recursion_limit(100):
            sequence([Done(v) for v in range(500)]).run()

    def test_filter_m(self):
        assert filter_m(lambda v: Done(v % 2 == 0), range(3)).run() == (0, 2)

    def test_map_m(self):
        assert map_m(Done, range(3)).run() == (0, 1, 2)
