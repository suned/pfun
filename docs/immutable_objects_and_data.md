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
In addition, if the `pfun` mypy plugin is enabled, mypy can check for assignments that will fail
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
