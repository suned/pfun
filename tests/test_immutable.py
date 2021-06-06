from dataclasses import FrozenInstanceError
from typing import Any

import pytest
from hypothesis import given

from pfun import Immutable
from pfun.hypothesis_strategies import anything


class C(Immutable):
    a: Any


class D(C):
    a2: Any


@given(anything())
def test_is_immutable(a):
    c = C(a)
    with pytest.raises(FrozenInstanceError):
        c.a = a


@given(anything(), anything())
def test_derived_is_immutable(a, a2):
    d = D(a, a2)
    with pytest.raises(FrozenInstanceError):
        d.a = a
    with pytest.raises(FrozenInstanceError):
        d.a2 = a2
