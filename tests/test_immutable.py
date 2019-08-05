import pytest
from hypothesis import given
from hypothesis.strategies import integers

from pfun import Immutable
from tests.strategies import anything


class C(Immutable):
    def __init__(self, a):
        self.a = a


class D(C):
    def __init__(self, a, a2):
        super().__init__(a)
        self.a2 = a2


@given(anything())
def test_is_immutable(a):
    c = C(a)
    with pytest.raises(AttributeError):
        c.a = a


@given(anything(), anything())
def test_derived_is_immutable(a, a2):
    d = D(a, a2)
    with pytest.raises(AttributeError):
        d.a = a
    with pytest.raises(AttributeError):
        d.a2 = a2


@given(anything(), anything())
def test_clone(initial, updated):
    c = C(initial)
    c = c.clone(a=updated)
    assert c.a == updated
    d = D(initial, initial)
    d = d.clone(a=updated, a2=updated)
    assert d.a == updated
    assert d.a2 == updated
