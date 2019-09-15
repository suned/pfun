from hypothesis import given, assume

from tests.monad_test import MonadTest
from pfun import state, identity, compose
from tests.strategies import anything, unaries, states


class TestState(MonadTest):
    @given(anything(), anything())
    def test_right_identity_law(self, value, init_state):
        assert (
            state.value(value).and_then(
                state.value
            ).run(init_state) == state.value(value).run(init_state)
        )

    @given(unaries(states()), anything(), anything())
    def test_left_identity_law(self, f, value, init_state):
        assert (
            state.value(value).and_then(f).run(init_state) ==
            f(value).run(init_state)
        )

    @given(states(), unaries(states()), unaries(states()), anything())
    def test_associativity_law(self, s, f, g, init_state):
        assert (
            s.and_then(f).and_then(g).run(init_state) ==
            s.and_then(lambda x: f(x).and_then(g)).run(init_state)
        )

    @given(anything(), anything())
    def test_equality(self, value, init_state):
        assert state.value(value).run(init_state
                                      ) == state.value(value).run(init_state)

    @given(anything(), anything(), anything())
    def test_inequality(self, first, second, init_state):
        assume(first != second)
        assert state.value(first).run(init_state
                                      ) != state.value(second).run(init_state)

    @given(anything(), anything())
    def test_identity_law(self, value, init_state):
        assert (
            state.value(value).map(identity).run(init_state) ==
            state.value(value).run(init_state)
        )

    @given(unaries(), unaries(), anything(), anything())
    def test_composition_law(self, f, g, value, init_state):
        h = compose(f, g)
        assert (
            state.value(value).map(h).run(init_state) ==
            state.value(value).map(g).map(f).run(init_state)
        )
