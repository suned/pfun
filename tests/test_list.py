import random

import pytest

from pfun import List, identity, compose
from pfun.list import with_effect, sequence, filter_m, map_m, value
from hypothesis.strategies import integers, lists as lists_
from hypothesis import given, assume
from .strategies import anything, unaries, lists
from .monad_test import MonadTest
from .monoid_test import MonoidTest
from .utils import recursion_limit


class TestList(MonadTest, MonoidTest):
    @given(lists(), lists())
    def test_append(self, l1, l2):
        assert l1.append(l2) == l1 + l2

    def test_empty(self):
        assert List().empty() == List()

    @given(lists())
    def test_left_append_identity_law(self, l):
        assert List() + l == l

    @given(lists_(anything()))
    def test_getitem(self, l):
        assume(l != [])
        assert l[0] == l[0]

    @given(lists())
    def test_right_append_identity_law(self, l):
        assert l + List() == l

    @given(lists(), lists(), lists())
    def test_append_associativity_law(self, x, y, z):
        assert (x + y) + z == x + (y + z)

    @given(lists(), unaries(lists()), unaries(lists()))
    def test_associativity_law(self, l: List, f, g):
        assert l.and_then(f).and_then(g) == l.and_then(
            lambda x: f(x).and_then(g)
        )

    @given(lists_(anything()))
    def test_equality(self, t):
        assert List(t) == List(t)

    @given(unaries(), unaries(), lists())
    def test_composition_law(self, f, g, l):
        h = compose(f, g)
        assert l.map(h) == l.map(g).map(f)

    @given(lists())
    def test_identity_law(self, l):
        assert l.map(identity) == l

    @given(lists_(anything()), lists_(anything()))
    def test_inequality(self, first, second):
        assume(first != second)
        assert List(first) != List(second)

    @given(anything(), unaries(lists()))
    def test_left_identity_law(self, v, f):
        assert List([v]).and_then(f) == f(v)

    @given(lists())
    def test_right_identity_law(self, l):
        assert l.and_then(lambda v: List([v])) == l

    @given(lists_(anything()))
    def test_reverse(self, l):
        assert List(l).reverse() == List(reversed(l))

    @given(lists_(anything()))
    def test_filter(self, l):
        def p(v):
            return id(v) % 2 == 0

        assert List(l).filter(p) == List(filter(p, l))

    @given(lists_(integers()))
    def test_reduce(self, l):
        i = sum(l)
        assert List(l).reduce(lambda a, b: a + b, 0) == i

    @given(lists(min_size=1), anything())
    def test_setitem(self, l, value):
        index = random.choice(range(len(l)))
        with pytest.raises(TypeError):
            l[index] = value

    @given(lists(min_size=1))
    def test_delitem(self, l):
        index = random.choice(range(len(l)))
        with pytest.raises(TypeError):
            del l[index]

    @given(lists(), lists_(anything()))
    def test_extend(self, l1, l2):
        assert l1.extend(l2) == l1 + l2

    @given(lists(), lists())
    def test_zip(self, l1, l2):
        assert List(l1.zip(l2)) == List(zip(l1, l2))

    def test_with_effect(self):
        @with_effect
        def f():
            a = yield value(2)
            b = yield value(2)
            return a + b

        assert f() == value(4)

        @with_effect
        def test_stack_safety():
            for _ in range(500):
                yield value(1)
            return None

        with recursion_limit(100):
            test_stack_safety()

    def test_sequence(self):
        assert sequence([value(v) for v in range(3)]) == value((0, 1, 2))

    def test_stack_safety(self):
        with recursion_limit(100):
            sequence([value(v) for v in range(500)])

    def test_filter_m(self):
        assert filter_m(lambda v: value(v % 2 == 0), range(3)) == value((0, 2))

    def test_map_m(self):
        assert map_m(value, range(3)) == value((0, 1, 2))
