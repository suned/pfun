import pytest
from hypothesis import given, assume
from hypothesis.strategies import integers

from pfun import curry


def f(a, b, c=1):
    return (a - b) / c


fc = curry(f)


@given(integers(), integers(), integers())
def test_non_curried_application(a, b, c):
    assume(c != 0)
    expected = f(a, b, c)
    assert fc(a, b, c) == expected
    assert fc(a=a, b=b, c=c) == expected
    assert fc(a=a, c=c, b=b) == expected
    assert fc(b=b, a=a, c=c) == expected
    assert fc(b=b, c=c, a=a) == expected
    assert fc(c=c, a=a, b=b) == expected
    assert fc(c=c, b=b, a=a) == expected


@given(integers(), integers())
def test_curried_application_no_defaults(a, b):
    expected = f(a, b)
    assert fc(a)(b) == expected
    assert fc(a=a)(b=b) == expected
    assert fc(b=b)(a=a) == expected


@given(integers(), integers(), integers())
def test_curried_application_with_defaults(a, b, c):
    assume(c != 0)
    expected = f(a, b, c)
    assert fc(a)(b, c=c) == expected
    assert fc(a, c=c)(b=b) == expected
    assert fc(a=a, c=c)(b=b) == expected
    assert fc(b=b, c=c)(a=a) == expected
    assert fc(c=c, b=b)(a=a) == expected
    assert fc(c=c)(b=b)(a=a) == expected
    assert fc(c=c)(b=b, a=a) == expected


def test_too_many_args():
    with pytest.raises(TypeError):
        fc(1, 2, 3, 4)


def test_wrong_keyword_arg():
    with pytest.raises(TypeError):
        fc(d=4)
