from hypothesis import given, assume
from pfun.free import Done, with_effect, sequence, map_m, filter_m, with_effect
from pfun import identity, compose

from .strategies import frees, unaries, anything
from .monad_test import MonadTest
from .utils import recursion_limit


class TestFree(MonadTest):
    @given(frees())
    def test_right_identity_law(self, free):
        assert free.and_then(Done) == free

    @given(anything(), unaries(frees()))
    def test_left_identity_law(self, value, f):
        assert Done(value).and_then(f) == f(value)

    @given(frees(), unaries(frees()), unaries(frees()))
    def test_associativity_law(self, free, f, g):
        assert free.and_then(f).and_then(g) == free.and_then(
            lambda x: f(x).and_then(g)
        )

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

    def test_with_effect(self):
        @with_effect
        def f():
            a = yield Done(2)
            b = yield Done(2)
            return a + b

        assert f() == Done(4)

        # TODO make stack safe
        # @with_effect
        # def test_stack_safety():
        #     for _ in range(500):
        #         yield Done(1)
        #     return None

        # with recursion_limit(100):
        #     test_stack_safety()

    def test_sequence(self):
        assert sequence([Done(v) for v in range(3)]) == Done((0, 1, 2))

    def test_stack_safety(self):
        with recursion_limit(100):
            sequence([Done(v) for v in range(500)])

    def test_filter_m(self):
        assert filter_m(lambda v: Done(v % 2 == 0), range(3)) == Done((0, 2))

    def test_map_m(self):
        assert map_m(Done, range(3)) == Done((0, 1, 2))
