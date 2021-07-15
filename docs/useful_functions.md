## curry
`curry` makes it easy to [curry](https://en.wikipedia.org/wiki/Currying) functions. If you enable the MyPy plugin, MyPy can also
type check the arguments and return types of curried functions.

The functions returned by `curry` support both normal and curried call styles:

```python
from pfun.functions import curry

@curry
def f(a: int, b: int) -> int:
    return a + b

assert f(2, 2) == 4
assert f(2)(2) == 4
```

Behind the scenes, `curry` simply uses `functools.partial` to partially
apply arguments until all required arguments are provided. This means
that when using optional and variadic arguments, there are _many_ different
ways to call a curried function:

```python
@curry
def f(a, b='b', c='c'):
    ...

assert f('a', c='c', b='b') == f(b='b')(a='a') == f(c='c')(a='a')(b='b') == ...
```
To keep things simple, the actual signature of curried functions is simply the original function signature,
which allows you to pass curried functions as arguments to functions that expects callbacks:

```python
from typing import Callable

from pfun import curry

@curry
def f(a: int, b: int) -> int: ...


def h(g: Callable[[int], int]) - int: ...

h(f(1))  # type safe
```

Because the signature of curried functions is not actually curried, this call will
currently issue a false type error:

```python
@curry
def f(a: int, b: int) -> int: ...


def h(g: Callable[[int], Callable[[int], int]]) -> int: ...


h(f)  # false type error
```

If you need to take curried functions as callback arguments, this is a type-safe
alternative
```python
from pfun.functions import Curry, curry

@curry
def f(a: int, b: int) -> int: ...

def h(g: Curry[Callable[[int, int], int]]) -> int: ...


h(f)  # type safe
```
Currently the `curry` MyPy plugin doesn't support methods. If you want to return a curried function from a method you can use the following workaround:

```python
from pfun.functions import Curry, curry


class C:
    def f(self, x: int) -> Curry[[Callable[[int], int]]]:
        return curry(lambda y: x + y)
```
## compose

`compose` makes it easy to compose functions while inferring the resulting type signature with MyPy (if the `pfun` MyPy plugin is enabled).
`compose` composes functions right to left:

```python
from pfun.functions import compose


def f(x):
    ...

def g(x):
    ...

h = compose(f, g)  # h == lambda x: f(g(x))
```
