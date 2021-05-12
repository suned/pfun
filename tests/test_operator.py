import operator
from typing import List, Tuple

from hypothesis import given
from hypothesis.strategies import (booleans, builds, data, integers, lists,
                                   tuples)

from pfun import operator as op


@given(integers(), integers())
def test_lt(a: int, b: int):
    assert op.lt(a)(b) == operator.lt(a, b)


@given(integers(), integers())
def test_le(a: int, b: int):
    assert op.le(a)(b) == operator.le(a, b)


@given(integers(), integers())
def test_eq(a: int, b: int):
    assert op.eq(a)(b) == operator.eq(a, b)


@given(integers(), integers())
def test_ne(a: int, b: int):
    assert op.ne(a)(b) == operator.ne(a, b)


@given(integers(), integers())
def test_gt(a: int, b: int):
    assert op.gt(a)(b) == operator.gt(a, b)


@given(booleans())
def test_not(a: bool):
    assert op.not_(a) == operator.not_(a)


@given(integers())
def test_truth(a: int):
    assert op.truth(a) == operator.truth(a)


@given(builds(object), builds(object))
def test_is(a: object, b: object):
    assert op.is_(a)(b) == operator.is_(a, b)


@given(builds(object), builds(object))
def test_is_not(a: object, b: object):
    assert op.is_not(a)(b) == operator.is_not(a, b)


@given(integers(), integers())
def test_add(a: int, b: int):
    assert op.add(a)(b) == operator.add(a, b)


@given(integers())
def test_abs(a: int):
    assert op.abs(a) == operator.abs(a)


@given(booleans(), booleans())
def test_and_(a: bool, b: bool):
    assert op.and_(a)(b) == operator.and_(a, b)


@given(tuples(integers()), integers())
def test_count_of(t: Tuple[int, ...], i: int):
    assert op.count_of(i)(t) == operator.countOf(t, i)


@given(integers(), integers())
def floordiv(a: int, b: int):
    assert op.floordiv(a)(b) == operator.floordiv(a, b)


@given(integers())
def test_index(a: int):
    assert op.index(a) == operator.index(a)


@given(integers())
def invert(a: int):
    assert op.invert(a) == operator.invert(a)


@given(integers(), integers(min_value=0))
def lshift(a: int, b: int):
    assert op.lshift(a)(b) == operator.lshift(a, b)


@given(integers(), integers())
def mod(a: int, b: int):
    assert op.mod(a)(b) == operator.mod(a, b)


@given(integers(), integers())
def mul(a: int, b: int):
    assert op.mul(a)(b) == operator.mul(a, b)


@given(integers(), integers())
def matmul(a: int, b: int):
    assert op.matmul(a)(b) == operator.matmul(a, b)


@given(integers())
def test_neg(a: int):
    assert op.neg(a) == operator.neg(a)


@given(booleans(), booleans())
def test_or_(a: bool, b: bool):
    assert op.or_(a)(b) == operator.or_(a, b)


@given(integers())
def test_pos(a: int):
    assert op.pos(a) == operator.pos(a)


@given(integers(), integers(min_value=1, max_value=100))
def test_pow(a: int, b: int):
    assert op.pow(a)(b) == operator.pow(a, b)


@given(integers(), integers(min_value=0))
def test_rshift(a: int, b: int):
    assert op.rshift(a)(b) == operator.rshift(a, b)


@given(integers(), integers())
def test_sub(a: int, b: int):
    assert op.sub(a)(b) == operator.sub(a, b)


@given(integers(), integers(min_value=1))
def test_truediv(a: int, b: int):
    assert op.truediv(a)(b) == operator.truediv(a, b)


@given(integers(), integers())
def test_xor(a: int, b: int):
    assert op.xor(a)(b) == operator.xor(a, b)


@given(data())
def test_getitem(data):
    a = data.draw(integers(min_value=1, max_value=100))
    t = data.draw(lists(integers(), min_size=a))
    assert op.get_item(a - 1)(t) == operator.getitem(t, a - 1)


@given(integers(), lists(integers()))
def test_contains(a: int, l: List[int]):
    assert op.contains(a)(l) == operator.contains(l, a)


@given(lists(integers()))
def test_length_hint(t: List[int]):
    assert op.length_hint(t) == operator.length_hint(t)
