from hypothesis import given, assume

from pfun import Dict
from pfun.maybe import Just, Nothing
from tests.strategies import dicts


@given(dicts())
def test_setitem(d):
    new_d = d.set('key', 'value')
    assert new_d == Dict(d).set('key', 'value')
    assert d != new_d
    assert 'key' not in d
    assert Dict({'key': 'value'}) == Dict().set('key', 'value')


@given(dicts())
def test_get_existing_key(d):
    d = d.set('key', 'value')
    assert d['key'] == Just('value')
    assert d.get('key') == Just('value')


@given(dicts())
def test_get_missing_key(d):
    assume('key' not in d)
    assert d['key'] == Nothing()
    assert d.get('key') == Nothing()


@given(dicts())
def test_update(d):
    assume('key' not in d)
    new_d = d.update({'key': 'value'})
    assert 'key' not in d
    assert new_d != d
    assert new_d['key'] == Just('value')
