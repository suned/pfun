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
A _lens_ is a setter function that takes as arguments a value to replace at some path/index
in an object/data-structure, and an object to transform. `pfun.lens` allows you
to easily construct these setter functions by specifying the path/index at
which you want to perform a replacement using normal Python indexing and attribute
access. You use the object returned by `lens()` as a proxy for the object you want
to transform by accessing attributes and indexes on it. The lens will remember this
path, and use it when performing an update. You perform an update by calling the lens
with the value to use as a replacement, and an object on which to perform the replacement:
```python
from pfun import lens


t = lens()['a']['b']['c']
new_d = t('Wow that was a lot easier!')(d)
assert new_d['a']['b']['c'] == 'Wow that was a lot easier!'
```
If you use the `pfun` MyPy plugin, you can give a type as an argument to `lens`, which allows MyPy to check that the operations you make on the lens object are supported by the type you intend to transform:
```python
class Person:
    name: str


class User(Person):
    organization: Organization


u = lens(User)

# MyPy type error because we misspelled 'organization'
u.organisation('Foo Inc')

# MyPy type error because "User.organization" must a "str"
u.organization(0)

# MyPy type error because "Person" is not a "User"
u.organization('Foo Inc')(Person())
```
Since lenses are just Python callables, you can combine them using the normal
compose operations available in `pfun`:
```python
from pfun import compose


class NamedUser(User):
    name: str


u = lens(NamedUser)
set_name = u.name
set_org_name = u.organization.name

new_user = compose(set_name('Bob'), set_org_name('Foo Inc'))(NamedUser())
```
Currently, `lens` supports working with the following types of objects and data-structures:

- Regular Python objects
- `collections.namedtuple` and `typing.NamedTuple` instances
- normal and frozen `dataclasses.dataclass` and `pfun.Immutable`
- `pfun.List`, `tuple` and `list`
- `pfun.Dict` and `dict`
