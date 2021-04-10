from string import printable

import pytest
from hypothesis import assume, given
from hypothesis.strategies import text

from pfun import Dict
from pfun.hypothesis_strategies import anything, dicts
from pfun.maybe import Just, Nothing


@given(dicts(text(printable), anything()))
def test_setitem(d):
    new_d = d.set('key', 'value')
    assert new_d == Dict(d).set('key', 'value')
    assert d != new_d
    assert 'key' not in d
    assert Dict({'key': 'value'}) == Dict().set('key', 'value')


@given(dicts(text(printable), anything()))
def test_get_existing_key(d):
    d = d.set('key', 'value')
    assert d['key'] == 'value'
    assert d.get('key') == Just('value')


@given(dicts(text(printable), anything()))
def test_get_missing_key(d):
    assume('key' not in d)

    with pytest.raises(KeyError):
        d['key']
    assert d.get('key') == Nothing()


@given(dicts(text(printable), anything()))
def test_update(d):
    assume('key' not in d)
    new_d = d.update({'key': 'value'})
    assert 'key' not in d
    assert new_d != d
    assert new_d['key'] == 'value'
