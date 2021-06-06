from typing import Any, NamedTuple

import pytest

from pfun import Dict, Immutable, List, lens


class VanillaClass:
    def __init__(self, attribute):
        self.attribute = attribute


class ImmutableClass(Immutable):
    attribute: Any


class NamedTupleClass(NamedTuple):
    attribute: Any


def test_pfun_list_root():
    l = List([-1])
    assert (lens()[0] << 1)(l) == List([1])
    assert l == List([-1])


def test_pfun_list_index_error():
    l = List([])
    with pytest.raises(IndexError):
        (lens()[0] << '')(l)


def test_pfun_nested_list():
    l = List([List([-1])])
    assert (lens()[0][0] << 1)(l) == List([List([1])])
    assert l == List([List([-1])])


def test_list_root():
    l = [-1]
    assert (lens()[0] << 1)(l) == [1]
    assert l == [-1]


def test_nested_list():
    l = [[0]]
    assert (lens()[0][0] << 1)(l) == [[1]]
    assert l == [[0]]


def test_tuple_root():
    t = (-1, )
    assert (lens()[0] << 1)(t) == (1, )
    assert t == (-1, )


def test_tuple_index_error():
    t = ()
    with pytest.raises(IndexError):
        (lens()[0] << 1)(t)


def test_nested_tuple():
    t = ((-1, ), )
    assert (lens()[0][0] << 1)(t) == ((1, ), )
    assert t == ((-1, ), )


def test_dict_root():
    d = {}
    assert (lens()['key'] << 'value')(d) == {'key': 'value'}
    assert d == {}


def test_nested_dict():
    d = {'key': {}}
    assert (lens()['key']['key'] << 'value')(d) == {'key': {'key': 'value'}}
    assert d == {'key': {}}


def test_pfun_dict_root():
    d = Dict({})
    assert (lens()['key'] << 'value')(d) == Dict({'key': 'value'})
    assert d == Dict({})


def test_nested_pfun_dict():
    d = Dict({'key': Dict({})})
    assert (lens()['key']['key'] << 'value')(d) == Dict(
        {'key': Dict({'key': 'value'})}
    )
    assert d == Dict({'key': Dict({})})


def test_vanilla_class_root():
    x = VanillaClass('a')
    assert (lens().attribute << 'b')(x).attribute == 'b'
    assert x.attribute == 'a'


def test_immutable_class_root():
    x = ImmutableClass('a')
    assert (lens().attribute << 'b')(x) == ImmutableClass('b')
    assert x == ImmutableClass('a')


def test_named_tuple_root():
    x = NamedTupleClass('a')
    assert (lens().attribute << 'b')(x) == NamedTupleClass('b')
    assert x == NamedTupleClass('a')


def test_pfun_list_attribute():
    x = VanillaClass(List([0]))
    assert (lens().attribute[0] << 1)(x).attribute == List([1])
    assert x.attribute == List([0])


def test_pfun_list_immutable_attribute():
    x = ImmutableClass(List([0]))
    assert (lens().attribute[0] << 1)(x) == ImmutableClass(List([1]))
    assert x == ImmutableClass(List([0]))


def test_list_attribute():
    x = VanillaClass([0])
    assert (lens().attribute[0] << 1)(x).attribute == [1]
    assert x.attribute == [0]


def test_list_immutable_attribute():
    x = ImmutableClass([0])
    assert (lens().attribute[0] << 1)(x) == ImmutableClass([1])
    assert x == ImmutableClass([0])


def test_tuple_attribute():
    x = VanillaClass((0, ))
    assert (lens().attribute[0] << 1)(x).attribute == (1, )
    assert x.attribute == (0, )


def test_tuple_immutable_attribute():
    x = ImmutableClass((0, ))
    assert (lens().attribute[0] << 1)(x).attribute == (1, )
    assert x == ImmutableClass((0, ))


def test_dict_attribute():
    x = VanillaClass({})
    assert (lens().attribute['key'] << 'value')(x).attribute == {
        'key': 'value'
    }
    assert x.attribute == {}


def test_dict_immutable_attribute():
    x = ImmutableClass({})
    assert (lens().attribute['key'] << 'value')(x) == ImmutableClass(
        {'key': 'value'}
    )
    assert x == ImmutableClass({})


def test_pfun_dict_attribute():
    x = VanillaClass(Dict({}))
    assert (lens().attribute['key'] << 'value')(x).attribute == Dict(
        {'key': 'value'}
    )
    assert x.attribute == Dict({})


def test_nested_vanilla():
    x = VanillaClass(VanillaClass('a'))
    assert (lens().attribute.attribute << 'b')(x).attribute.attribute == 'b'
    assert x.attribute.attribute == 'a'


def test_nested_immutable():
    x = ImmutableClass(ImmutableClass('a'))
    assert (lens().attribute.attribute << 'b')(x) == ImmutableClass(
        ImmutableClass('b')
    )
    assert x == ImmutableClass(ImmutableClass('a'))


def test_nested_named_tuple():
    x = NamedTupleClass(NamedTupleClass('a'))
    assert (lens().attribute.attribute << 'b')(x) == NamedTupleClass(
        NamedTupleClass('b')
    )
    assert x == NamedTupleClass(NamedTupleClass('a'))
