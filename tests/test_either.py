from typing import Any

from hypothesis import assume, given

from pfun import Unary, compose, identity
from pfun.either import (Either, Left, Right, either, filter_, for_each,
                         sequence)
from tests.monad_test import MonadTest
from tests.strategies import anything, eithers, unaries

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

        assert either.and_then(f).and_then(
            g
        ) == either.and_then(  # type: ignore
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

    def test_sequence(self):
        assert sequence([Right(v) for v in range(3)]) == Right((0, 1, 2))

    def test_stack_safety(self):
        with recursion_limit(100):
            sequence([Right(v) for v in range(500)])

    def test_filter(self):
        assert filter_(lambda v: Right(v % 2 == 0), range(3)) == Right((0, 2))

    def test_for_each(self):
        assert for_each(Right, range(3)) == Right((0, 1, 2))
