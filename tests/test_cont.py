from hypothesis import assume, given

from pfun import compose, cont, identity
from tests.monad_test import MonadTest
from tests.strategies import anything, conts, unaries

from .utils import recursion_limit


class TestCont(MonadTest):
    @given(anything())
    def test_right_identity_law(self, value):
        assert (
            cont.value(value).and_then(
                cont.value
            ).run(identity) == cont.value(value).run(identity)
        )

    @given(unaries(conts()), anything())
    def test_left_identity_law(self, f, value):
        assert (
            cont.value(value).and_then(f).run(identity) == f(value
                                                             ).run(identity)
        )

    @given(conts(), unaries(conts()), unaries(conts()))
    def test_associativity_law(self, c, f, g):
        assert (
            c.and_then(f).and_then(g).run(identity) ==
            c.and_then(lambda x: f(x).and_then(g)).run(identity)
        )

    @given(anything())
    def test_equality(self, value):
        assert cont.value(value).run(identity) == cont.value(value
                                                             ).run(identity)

    @given(anything(), anything())
    def test_inequality(self, first, second):
        assume(first != second)
        assert cont.value(first).run(identity) != cont.value(second
                                                             ).run(identity)

    @given(anything())
    def test_identity_law(self, value):
        assert (
            cont.value(value).map(identity).run(identity) ==
            cont.value(value).run(identity)
        )

    @given(unaries(), unaries(), anything())
    def test_composition_law(self, f, g, value):
        h = compose(f, g)
        assert (
            cont.value(value).map(h).run(identity) ==
            cont.value(value).map(g).map(f).run(identity)
        )

    def test_with_effect(self):
        @cont.with_effect
        def f():
            a = yield cont.value(2)
            b = yield cont.value(2)
            return a + b

        assert f().run(identity) == 4

        @cont.with_effect
        def test_stack_safety():
            for _ in range(500):
                yield cont.value(1)
            return None

        with recursion_limit(100):
            test_stack_safety().run(identity)

    def test_sequence(self):
        assert (
            cont.sequence([cont.value(v)
                           for v in range(3)]).run(identity) == (0, 1, 2)
        )

    def test_stack_safety(self):
        with recursion_limit(100):
            cont.sequence([cont.value(v) for v in range(500)]).run(identity)

    def test_filter_m(self):
        assert cont.filter_m(lambda v: cont.value(v % 2 == 0),
                             range(3)).run(identity) == (0, 2)

    def test_map_m(self):
        assert cont.map_m(cont.value, range(3)).run(identity) == (0, 1, 2)
