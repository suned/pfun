from typing import Any

from hypothesis import assume, given

from pfun import List, Unary, compose, identity
from pfun.maybe import (Just, Maybe, Nothing, filter_m, flatten, map_m, maybe,
                        sequence, with_effect)

from .monad_test import MonadTest
from .strategies import anything, lists, maybes, unaries
from .utils import recursion_limit


class TestMaybe(MonadTest):
    def test_equality(self):
        self._test_just_equality()
        self._test_nothing_equality()

    def test_inequality(self):
        self._test_just_inequality()
        self._test_nothing_inequality()

    def test_identity_law(self):
        self._test_just_identity_law()
        self._test_nothing_identity_law()

    @given(maybes())
    def test_right_identity_law(self, maybe: Maybe):
        assert maybe.and_then(Just) == maybe

    @given(anything(), unaries(maybes()))
    def test_left_identity_law(self, value, f: Unary[Any, Maybe]):
        assert Just(value).and_then(f) == f(value)

    @given(maybes(), unaries(maybes()), unaries(maybes()))
    def test_associativity_law(
        self, maybe: Maybe, f: Unary[Any, Maybe], g: Unary[Any, Maybe]
    ):
        assert maybe.and_then(f).and_then(g) == maybe.and_then(  # type: ignore
            lambda x: f(x).and_then(g)
        )

    @given(anything())
    def _test_just_equality(self, value):
        assert Just(value) == Just(value)

    def _test_nothing_equality(self):
        assert Nothing() == Nothing()

    @given(anything())
    def _test_just_inequality(self, value):
        assert Just(value) != Nothing()

    @given(anything(), anything())
    def _test_nothing_inequality(self, first, second):
        assume(first != second)
        assert Just(first) != Just(second)

    @given(anything())
    def _test_just_identity_law(self, value):
        assert Just(value).map(identity) == Just(value)

    def _test_nothing_identity_law(self):
        assert Nothing().map(identity) == Nothing()

    @given(unaries(), unaries(), anything())
    def test_composition_law(self, f: Unary, g: Unary, value):
        h = compose(f, g)
        assert Just(value).map(h) == Just(value).map(g).map(f)
        assert Nothing().map(h) == Nothing().map(g).map(f)

    @given(anything())
    def test_just_or_else(self, value):
        assert Just(value).or_else(None) == value

    @given(anything())
    def test_nothing_or_else(self, value):
        assert Nothing().or_else(value) is value

    def test_maybe_decorater(self):
        maybe_int = maybe(int)
        assert maybe_int('1') == Just(1)
        assert maybe_int('whoops') == Nothing()

    @given(anything())
    def test_just_bool(self, value):
        assert bool(Just(value))

    def test_nothing_bool(self):
        assert not bool(Nothing())

    @given(lists([maybes()]))
    def test_flatten(self, maybe_list):
        assert flatten(maybe_list) == List(m.get for m in maybe_list if m)

    def test_with_effect(self):
        @with_effect
        def f():
            a = yield Just(2)
            b = yield Just(2)
            return a + b

        assert f() == Just(4)

        @with_effect
        def g():
            a = yield Just(2)
            b = yield Nothing()
            return a + b

        assert g() == Nothing()

        @with_effect
        def test_stack_safety():
            for _ in range(500):
                yield Just(1)
            return None

        with recursion_limit(100):
            test_stack_safety()

    def test_sequence(self):
        assert sequence([Just(v) for v in range(3)]) == Just((0, 1, 2))

    def test_stack_safety(self):
        with recursion_limit(100):
            sequence([Just(v) for v in range(500)])

    def test_filter_m(self):
        assert filter_m(lambda v: Just(v % 2 == 0), range(3)) == Just((0, 2))

    def test_map_m(self):
        assert map_m(Just, range(3)) == Just((0, 1, 2))
