## Immutable

`Immutable` makes a class (and all classes that inherit from it) immutable. The syntax is much the same
as for `dataclass` or `NamedTuple`:

```python
from pfun.immutable import Immutable


class C(Immutable):
    a: int

class D(C):
    b: int

c = C(1)
c.a = 2  # raises: FrozenInstanceError

d = D(2, 2)  # 'D' inherits the members of C
d.b = 2  # raises FrozenInstanceError
```

`Immutable` uses [dataclasses](https://docs.python.org/3/library/dataclasses.html) under the hood, so for detailed
usage documentation, see the official docs. You can use the entire `dataclass` api.

```python
from dataclasses import field
from typing import Tuple

class C(Immutable):
    l: Tuple[int] = field(default_factory=tuple)


assert C().l == ()
```
In addition, if the `pfun` MyPy plugin is enabled, MyPy can check for assignments that will fail
at runtime.

## List
`List` is a functional style list data structure.
```python
from pfun.list import List

l = List(range(5))
l2 = l.append(5)
assert l == List(range(5)) and l2 == List(range(6))
```
It supports the same operations as `list`, with the exception of `__setitem__`, which
will raise an Exception.

In addition, `List` supplies functional operations such as `map` and `reduce` as
instance methods

```python
assert List(range(3)).reduce(lambda a, b: a + b) == 3
assert List(range(3)).map(str) == ['0', '1', '2']
```
## Dict
`Dict` is a functional style dictionary.

```python
from pfun.dict import Dict
from pfun.maybe import Just

d = Dict({'key': 'value'})
d2 = d.set('new_key', 'new_value')
assert 'new_key' not in d and d2.get('new_key') == Just('new_value')
```

It supports the same api as `dict` which the exception of `__setitem__` which will raise an exception, and uses
`pfun.maybe.Maybe` to indicate the presence or absence of a key when using `get`.

## Lens
Working with deeply nested immutable data-structures can be tricky when you want to transform only one member of an object deep inside the nested structure, but want to keep other the remaining data-structure intact, for example in:

```python
d = {
    'a': {
        'b': {
            'c': 'I want to change this...'
        }
    },
    'd': 'but not this'
}
new_d = d.copy()
new_d['a'] = d['a'].copy()
new_d['a']['b'] = d['a']['b'].copy()
new_d['a']['b']['c'] = 'Phew! That took a lot of work!'
```
`pfun.lens` gives you an object that allows you to "zoom in" on some field in a data-structure, and copy only what is necessary to change what you want without altering the original object. You use the lens object as a proxy for the object you want to transform, and "set" values using the `<<` operator, which returns a transformation function that you can apply to the data-structure:

```python
from pfun import lens


l = lens()
t = l['a']['b']['c'] << 'Wow, that was a lot easier!'
new_d = t(d)
```
If you use the `pfun` MyPy plugin, you can give a type as an argument to `lens`, which allows MyPy to check that the operations you make on the lens object are supported by the type you intend to transform:
```python
class Person:
    name: str


class User(Person):
    organization: str


u = lens(User)

# MyPy type error because we misspelled 'organization'
u.organisation << 'Foo Inc'


# MyPy type error because "Person" is not a "User"
(u.organization << 'Foo Inc')(Person())
```

Currently, `lens` supports working the following types of objects and data-structures:

- Regular Python objects
- `collections.namedtuple` and `typing.NamedTuple` instances
- normal and frozen `dataclasses.dataclass` and `pfun.Immutable`
- `pfun.List`, `tuple` and `list`
- `pfun.Dict` and `dict`
