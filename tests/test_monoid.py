from hypothesis import given
from hypothesis.strategies import builds, integers, lists, none, text, tuples

from pfun.monoid import Monoid, append, empty
from tests.strategies import anything


class M(Monoid):
    def __init__(self, i):
        self.i = i

    def __add__(self, other: 'M') -> 'M':
        return M(self.i + other.i)

    def empty(self) -> 'M':
        return M(0)


def ms():
    return builds(M, integers())


@given(ms(), ms())
def test_monoid(m1, m2):
    assert empty(m1).i == 0
    assert append(m1, m1.empty()).i == m1.i
    assert append(m1.empty(), m1).i == m1.i
    assert append(m1, m2).i == m1.i + m2.i
    assert append(m2, m1).i == m2.i + m1.i


@given(lists(anything()), lists(anything()))
def test_list(l1, l2):
    assert empty(l1) == []
    assert append(l1, []) == l1
    assert append([], l1) == l1
    assert append(l1, l2) == l1 + l2
    assert append(l2, l1) == l2 + l1


@given(integers(), integers())
def test_int(i1, i2):
    assert empty(i1) == 0
    assert append(0, i1) == i1
    assert append(i1, 0) == i1
    assert append(i1, i2) == i1 + i2
    assert append(i2, i1) == i2 + i1


@given(text(), text())
def test_str(s1, s2):
    assert empty(s1) == ''
    assert append(s1, '') == s1
    assert append('', s1) == s1
    assert append(s1, s2) == s1 + s2
    assert append(s2, s1) == s2 + s1


@given(none(), none())
def test_none(n1, n2):
    assert empty(n1) is None
    assert append(n1, None) is None
    assert append(None, n1) is None
    assert append(n1, n2) is None
    assert append(n2, n1) is None


@given(tuples(), tuples())
def test_tuple(t1, t2):
    assert empty(t1) == ()
    assert append(t1, ()) == t1
    assert append((), t1) == t1
    assert append(t1, t2) == t1 + t2
    assert append(t2, t1) == t2 + t1
