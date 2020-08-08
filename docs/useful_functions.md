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

To keep things simple, the `pfun` MyPy plugin doesn't infer all possible overloads of curried signatures. Instead, the inferred signature is split into the following argument lists: One argument list for optional arguments and `**kwargs` followed by one argument list for each positional argument. If the uncurried function accepts `*args`, it's added to the last positional argument list of the curried function

In other words, given the following function `f`:
```python
@curry
def f(pos_1: T, pos_2: T, *args: T, keyword: T = '', **kwargs: T) -> T:
    ...
```
the MyPy plugin infers the following overloaded signatures:

- **Curried signature without optional arguments**  
`(pos_1: T) -> (pos_2: T, *args: T) -> T`
- **Curried signature with optional arguments**  
`(*, keyword: T =, **kwargs: T) -> (pos_1: T) -> (pos_2: T, *args: T) -> T`
- **Uncurried signature**  
`(pos_1: T, pos_2: T, *args: T, *, keyword: T =, **kwargs: T) -> T`

The reasoning behind this behaviour is that the main use-case for currying is
to pass partially applied functions as arguments to other functions that expect
unary function arguments such as `pfun.effect.Effect.map` ar `pfun.effect.Effect.and_then`,
and in by-far most cases, we need the required arguments to be applied last:

```python
import operator as op
from pfun.functions import curry
from pfun.effect import success

success(2).map(curry(op.add)(2)).run(None)
4
```

If this is not the behaviour you need, you can cast the result of calling a curried function,
or use a `lambda`:
```python
from typing import cast, Callable


@curry
def only_optional_args(a: str = 'a', b: str = 'b') -> str:
    ...

# we need to cast here because the MyPy plugin does not infer this signature
f = cast(Callable[[str], str], only_optional_args('c'))

# alternatively, use a lambda
f = lambda b: only_optional_args('c', b)
```
