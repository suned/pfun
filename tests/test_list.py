from pfun import List, identity, compose
from hypothesis.strategies import integers, lists as lists_
from hypothesis import given, assume
from .strategies import anything, unaries, lists
from .monad_test import MonadTest
from .monoid_test import MonoidTest


class TestList(MonadTest, MonoidTest):
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
        assert l.and_then(f).and_then(g) == l.and_then(lambda x: f(x).and_then(g))

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
