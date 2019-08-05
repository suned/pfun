from typing import Any

from hypothesis import given, assume

from pfun import Unary, identity, compose
from pfun.result import Result, Ok, Error
from tests.monad_test import MonadTest
from tests.strategies import results, unaries, anything


class TestResult(MonadTest):
    @given(results())
    def test_right_identity_law(self, result: Result):
        assert result.and_then(Ok) == result

    @given(anything(), unaries(results()))
    def test_left_identity_law(self, value, f: Unary[Any, Result]):
        assert Ok(value).and_then(f) == f(value)

    @given(results(), unaries(results()), unaries(results()))
    def test_associativity_law(self,
                               result: Result,
                               f: Unary[Any, Result],
                               g: Unary[Any, Result]):

        assert result.and_then(f).and_then(g) == result.and_then(lambda x: f(x).and_then(g))

    @given(anything())
    def test_equality(self, value):
        assert Ok(value) == Ok(value)
        assert Error(value) == Error(value)

    @given(anything(), anything())
    def test_inequality(self, first, second):
        assume(first != second)
        assert Ok(first) != Ok(second)
        assert Error(first) != Error(second)
        assert Ok(first) != Error(first)

    @given(anything())
    def test_identity_law(self, value):
        assert Ok(value).map(identity) == Ok(value)
        assert Error(value).map(identity) == Error(value)

    @given(unaries(), unaries(), anything())
    def test_composition_law(self, f: Unary, g: Unary, value):
        h = compose(f, g)
        assert Ok(value).map(h) == Ok(value).map(g).map(f)
        assert Error(value).map(h) == Error(value).map(g).map(f)

