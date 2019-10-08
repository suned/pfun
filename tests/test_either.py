from typing import Any

from hypothesis import given, assume

from pfun import Unary, identity, compose
from pfun.either import (
    Either, Left, Right, either, with_effect, sequence, filter_m, map_m
)
from tests.monad_test import MonadTest
from tests.strategies import eithers, unaries, anything
from .utils import recursion_limit


class TestEither(MonadTest):
    @given(eithers())
    def test_right_identity_law(self, either: Either):
        assert either.and_then(Right) == either

    @given(anything(), unaries(eithers()))
    def test_left_identity_law(self, value, f: Unary[Any, Either]):
        assert Right(value).and_then(f) == f(value)

    @given(eithers(), unaries(eithers()), unaries(eithers()))
    def test_associativity_law(
        self, either: Either, f: Unary[Any, Either], g: Unary[Any, Either]
    ):

        assert either.and_then(f).and_then(g) == either.and_then(
            lambda x: f(x).and_then(g)
        )

    @given(anything())
    def test_equality(self, value):
        assert Left(value) == Left(value)
        assert Right(value) == Right(value)

    @given(anything(), anything())
    def test_inequality(self, first, second):
        assume(first != second)
        assert Left(first) != Left(second)
        assert Right(first) != Right(second)
        assert Left(first) != Right(first)

    @given(anything())
    def test_identity_law(self, value):
        assert Left(value).map(identity) == Left(value)
        assert Right(value).map(identity) == Right(value)

    @given(unaries(), unaries(), anything())
    def test_composition_law(self, f: Unary, g: Unary, value):
        h = compose(f, g)
        assert Left(value).map(h) == Left(value).map(g).map(f)
        assert Right(value).map(h) == Right(value).map(g).map(f)

    @given(anything(), anything())
    def test_or_else(self, value, default):
        assert Right(value).or_else(default) == value
        assert Left(value).or_else(default) == default

    @given(anything())
    def test_bool(self, value):
        assert bool(Right(value))
        assert not bool(Left(value))

    def test_either_decorator(self):
        result_int = either(int)
        assert result_int('1') == Right(1)

    def test_with_effect(self):
        @with_effect
        def f():
            a = yield Right(2)
            b = yield Right(2)
            return a + b

        assert f() == Right(4)

        @with_effect
        def g():
            a = yield Right(2)
            b = yield Left('error')
            return a + b

        assert g() == Left('error')

        @with_effect
        def test_stack_safety():
            for _ in range(500):
                yield Right(1)
            return None

        with recursion_limit(100):
            test_stack_safety()

    def test_sequence(self):
        assert sequence([Right(v) for v in range(3)]) == Right((0, 1, 2))

    def test_stack_safety(self):
        with recursion_limit(100):
            sequence([Right(v) for v in range(500)])

    def test_filter_m(self):
        assert filter_m(lambda v: Right(v % 2 == 0), range(3)) == Right((0, 2))

    def test_map_m(self):
        assert map_m(Right, range(3)) == Right((0, 1, 2))
