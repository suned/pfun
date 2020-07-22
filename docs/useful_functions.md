## compose

`compose` makes it easy to compose functions while inferring the resulting type signature with mypy (if the `pfun` mypy plugin is enabled).
`compose` composes functions right to left:

```python
from pfun.functions import compose


def f(x):
    ...

def g(x):
    ...

h = compose(f, g)  # h == lambda x: f(g(x))
```

## curry
`curry` makes it easy to [curry](https://en.wikipedia.org/wiki/Currying) functions while inferring the resulting type signature with mypy (if the `pfun` mypy plugin is enabled).
The functions returned by `curry` support both normal and curried call styles:

```python
from pfun.functions import curry

@curry
def f(a: int, b: int, c: int = 2) -> int:
    return a + b * c

assert f(1, 1) == 3
assert f(1)(1) == 3
```
