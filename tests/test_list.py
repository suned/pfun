import builtins
import random

import pytest
from hypothesis import assume, given, settings
from hypothesis.strategies import integers
from hypothesis.strategies import lists as lists_

from pfun import List, compose, identity
from pfun.hypothesis_strategies import anything, lists, unaries
from pfun.list import filter_, for_each, gather, value

from .monad_test import MonadTest
from .utils import recursion_limit


class TestList(MonadTest):
    @given(lists(anything()), anything())
    def test_append(self, l1, l2):
        assert l1.append(l2) == l1 + (l2, )

    def test_empty(self):
        assert List().empty() == List()

    @given(lists(anything()))
    def test_left_append_identity_law(self, l):
        assert List() + l == l

    @given(lists_(anything()))
    def test_getitem(self, l):
        assume(l != [])
        assert l[0] == l[0]

    @given(lists(anything()))
    def test_right_append_identity_law(self, l):
        assert l + List() == l

    @given(lists(anything()), lists(anything()), lists(anything()))
    def test_append_associativity_law(self, x, y, z):
        assert (x + y) + z == x + (y + z)

    @settings(deadline=None)
    @given(
        lists(anything()),
        unaries(lists(anything())),
        unaries(lists(anything()))
    )
    def test_associativity_law(self, l: List, f, g):
        assert l.and_then(f).and_then(g) == l.and_then(
            lambda x: f(x).and_then(g)
        )

    @given(lists_(anything()))
    def test_equality(self, t):
        assert List(t) == List(t)

    @given(unaries(anything()), unaries(anything()), lists(anything()))
    def test_composition_law(self, f, g, l):
        h = compose(f, g)
        assert l.map(h) == l.map(g).map(f)

    @given(lists(anything()))
    def test_identity_law(self, l):
        assert l.map(identity) == l

    @given(lists_(anything()), lists_(anything()))
    def test_inequality(self, first, second):
        assume(first != second)
        assert List(first) != List(second)

    @given(anything(), unaries(lists(anything())))
    def test_left_identity_law(self, v, f):
        assert List([v]).and_then(f) == f(v)

    @given(lists(anything()))
    def test_right_identity_law(self, l):
        assert l.and_then(lambda v: List([v])) == l

    @given(lists_(anything()))
    def test_reverse(self, l):
        assert List(l).reverse() == List(reversed(l))

    @given(lists_(anything()))
    def test_filter(self, l):
        def p(v):
            return id(v) % 2 == 0

        assert List(l).filter(p) == List(builtins.filter(p, l))

    @given(lists_(integers()))
    def test_reduce(self, l):
        i = sum(l)
        assert List(l).reduce(lambda a, b: a + b, 0) == i

    @given(lists(anything(), min_size=1), anything())
    def test_setitem(self, l, value):
        index = random.choice(range(len(l)))
        with pytest.raises(TypeError):
            l[index] = value

    @given(lists(anything(), min_size=1))
    def test_delitem(self, l):
        index = random.choice(range(len(l)))
        with pytest.raises(TypeError):
            del l[index]

    @given(lists(anything()), lists_(anything()))
    def test_extend(self, l1, l2):
        assert l1.extend(l2) == l1 + l2

    @given(lists(anything()), lists(anything()))
    def test_zip(self, l1, l2):
        assert List(l1.zip(l2)) == List(zip(l1, l2))

    def test_gather(self):
        assert gather([value(v) for v in range(3)]) == value((0, 1, 2))

    def test_stack_safety(self):
        with recursion_limit(100):
            gather([value(v) for v in range(500)])

    def test_filter_(self):
        assert filter_(lambda v: value(v % 2 == 0), range(3)) == value((0, 2))

    def test_for_each(self):
        assert for_each(value, range(3)) == value((0, 1, 2))
