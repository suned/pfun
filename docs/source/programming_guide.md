# Guide
This section gives you an overview over functional programming and
static type checking with `pfun`. This is a good place to start, especially if you're new to functional programming.
For a detailed documentation of all classes and functions, see [API Reference](api_reference.html).

## Install

`pip install pfun`

### MyPy Plugin

The types provided by the Python `typing` module are often not flexible enough to provide
precise typing of common functional design patterns. If you use [mypy](http://mypy-lang.org/), `pfun`
provides a plugin that enables more precise types which can identify more bugs caused by
type errors. To enable the `pfun` mypy plugin,
add the following to you mypy configuration:
```
[mypy]
plugins = pfun.mypy_plugin
```

## Immutable Objects and Data Structures
### Immutable

`Immutable` makes a class (and all classes that inherit from it) immutable. The syntax is much the same
as for `dataclass` or `NamedTuple`:

```python
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
usage documentation, see the official documentation. You can use the entire `dataclass` api.

```python
from dataclasses import field
from typing import Tuple

class C(Immutable):
    l: Tuple[int] = field(default_factory=tuple)


assert C().l == ()
```
In addition, if the `pfun` mypy plugin is enabled, mypy can check for assignments that will fail
at runtime.

### List
`List` is a functional style list data structure.
```python
from pfun import List

l = List(range(5))
l2 = l.append(5)
assert l == List(range(5)) and l2 == List(range(6))
```
It supports the same operations as `list`, with the exception of `__setitem__`, which
will raise an Exception.

In addition, `List` supplies functional operations such as `map` and `reduce` as
instance methods

```python
assert List(range(3)).reduce(sum) == 3
assert List(range(3)).map(str) == ['0', '1', '2']
```
### Dict
`Dict` is a functional style dictionary.

```python
from pfun import Dict

d = Dict(key='value')
d2 = d.set('new_key', 'new_value')
assert 'new_key' not in d and d2['new_key'] == Just('new_value')
```

It supports the same api as `dict` which the exception of `__setitem__` which will raise an exception, and uses
`pfun.maybe.Maybe` to indicate the presence or absence of a key.

## Useful Functions
### compose

`compose` makes it easy to compose functions while inferring the resulting type signature with mypy (if the `pfun` mypy plugin is enabled).
`compose` composes functions right to left:

```python
from pfun import compose


def f(x):
    ...

def g(x):
    ...

h = compose(f, g)  # h == lambda x: f(g(x))
```

### curry
`curry` makes it easy to curry functions while inferring the resulting type signature with mypy (if the `pfun` mypy plugin is enabled).
The functions returned by `curry` support both normal and curried call styles:

```python
from pfun import curry

@curry
def f(a: int, b: int, c: int = 2) -> int:
    return a + b * c

assert f(1, 1) == 3
assert f(1)(1) == 3
```

## Effectful (But Side-Effect Free) Functional Programming
### Maybe
Say you have a function that can fail:

```python
def i_can_fail(v: str) -> str:
    if v == 'illegal value':
        raise ValueError()
    return 'Ok!'
```
We already added type annotations to the `i_can_fail` function, but there is really no way for the caller
to see that this function can fail from the type signature alone (and hence also no way for your favorite PEP 484 type-checker).

Wouldn't it be nice if the type signature of `i_can_fail` could give you that information? Then you wouldn't need to read the
entire function to know which error cases to cover,
and you could even get a type checker to help you. The `Maybe` type is designed to do just that:

```python
from pfun.maybe import (
    Maybe,
    Just,    # Class that represents success
    Nothing  # Class that represents failure
)

def i_can_fail(v: str) -> Maybe[str]:
    if v == 'illegal value':
        return Nothing()
    return Just('Ok!')
```

Technically speaking, `Maybe` is a _monad_. In addition to making effects such as errors explicit
by putting them in the type signature, all monadic types like `Maybe` supports a function called `and_then` which allows you to
chain together effectful functions that keeps track of the effects along the way automatically
without any mutable state.

```python
def reverse(s: str) -> Maybe[str]:
    reversed_string = ''.join(reversed(s))
    return Just(reversed_string)

assert i_can_fail('arg').and_then(reverse) == Just('!kO')
assert i_can_fail('illegal value').and_then(reverse) == Nothing()
```
Neat!

In other frameworks, `and_then` is often called `bind`.
The only requirement for the function argument to `and_then` is that it returns the same
monadic type that you started with (a `Maybe` in this case).
A function that returns a monadic value is called a _monadic function_.

### Either
`Maybe` allowed us to put the failure effect in the type signature, but
it doesn't tell the caller _what_ went wrong. `Either` will do that:

```python
from pfun.Either import Right, Left, Either


def i_can_fail(s: str) -> Either[ValueError, str]:
    if s == 'illegal value':
        return Left(ValueError())
    return Right('Ok!')
```

### Reader
Imagine that you're trying to write a Python program in functional style.
In many places in your code, you need to instantiate dependencies
(like a database connection). You could of course instantiate that
class wherever you need it

```python
from database_library import Connection

def f() -> str:
    data = Connection('host:user:password').get_data()
    return do_something(data)
```

But you quickly realise that this makes the code hard to reuse. What if you want to
run the same code against a new database?
What if you want to unit test your code without actually connecting to the database?

You decide to instead take the connection instance as an argument,
that way making the caller responsible for supplying the connection.

```python
def f(connection: Connection) -> str:
    data = connection.get_data()
    return do_something(data)
```
But now you have to pass that parameter around through potentially many function calls
that don't use it for anything other than passing to `f`

```python
def calls_f(connection: Connection) -> str:
    ...
    return f(connection)

def main():
    connection = Connection('host:user:password')
    result = calls_f(connection)
    print(result)
```
Ugh. There has to be a better way. With the `Reader` monad there is

```python
from pfun.reader import value, ask, Reader


def f() -> Reader[Connection, str]:
    def _(c):
        data = c.get_data()
        return value(do_something(data))

    return ask().and_then(_)


def calls_f() -> Reader[Connection, str]:
    ...
    return f()


def main():
    connection = Connection('host:user:password')
    result = calls_f().run(connection)
    print(result)
```


### Writer
Imagine that you are logging by appending to a `tuple` (Why a `tuple`? Well because they're
immutable of course!). Trying to avoid global mutable state,
you decide to pass the list around as a common argument to all the functions
in your program that needs to do logging
```python
from typing import Tuple
def i_need_to_log_something(i: int, log: Tuple[str]) -> Tuple[int, Tuple[str]]:
    result = compute_something(i)
    log = log + ('Something was successfully computed',)
    return result, log
 
def i_need_to_log_something_too(i: int, log: Tuple[str]) -> Tuple[int, Tuple[str]]:
    result = compute_something_else(i)
    log = log + ('Something else was computed',)
    return result, log


def main():
    result, log = i_need_to_log_something(1, ())
    result, log = i_need_to_log_something_too(result, log)
    print('result', result)
    print('log', log)
```
Well that obviously works, but there is a lot of logistics involved that seems
like it should be possible to abstract. This is what `Writer` will do for you:

```python
from typing import List
from pfun.writer import value, Writer


def i_need_to_log_something(i: int) -> Writer[int, List[str]]:
    result = compute_something(i)
    return Writer(result, ['Something was successfully computed'])
    
    
def i_need_to_log_something_too(i: int) -> Writer[int, List[str]]:
    result = compute_something_else(i)
    return Writer(result, ['Something else was successfully computed'])


def main():
    _, log = i_need_to_log_something(1).and_then(i_need_to_log_something_too)
    print('log', log)  # output: ['Something was successfully computed', 'Something else was successfully computed']
 
```
`tuple` is not the only thing `Writer` can combine: in fact the only requirement on the second argument is that its a _monoid_. You can even tell writer
to combine custom types by implementing the `Monoid` ABC.

### State
Where `Reader` can only read the context passed into it, and `Writer` can only append to a monoid but not read it, `State` can do both.
You can use it to thread some state through a computation without global shared state

```python
from pfun.state import value, put, get, State

def add(item: str) -> State[None, tuple]:
    return get().and_then(lambda t: put(t + (item,)))

def remove_first() -> State[None, tuple]:
    return get().and_then(lambda t: put(t[1:]))

state = add('first element').and_then(
    lambda _: add('second_element')
).and_then(
    lambda _: remove_first()
)
print(state.run(()))  # outputs (None, ('second element',))
```
The `None` value is the result of the computation (which is nothing, because all we do is change the state), and `('second element',)` is the final state.
### IO
A program that can't interact with the outside world isn't much use. But how can we keep our program pure and still interact with
the outside world? The common solution is to use `IO` to separate the pure parts of our program from the unpure parts

```python
from pfun.io import get_line, put_line, IO

name: IO[str] = get_line('What is you name? ')
greeting: IO[str] = name.map(lambda s: 'Hello ' + s)
print_: IO[None] = greeting.and_then(put_line)
print_.run()
```

`get_line` creates an `IO` action that when run, will read a `str` from standard input. `IO` can be combined
with `map` and `and_then` just like the other monads we have seen.


### Combining Monadic Values
Sometimes you want to combine multiple unwrapped monadic values 
like in the `get_full_name` function below:
```python
from pfun.maybe import Just, Maybe

def get_first_name() -> Maybe[str]:
    ...

def get_last_name() -> Maybe[str]:
    ...

def get_full_name() -> Maybe[str]:
    return get_first_name().and_then(
        lambda first: get_last_name().and_then(
            lambda last: return Just(first + ' ' + last)
        )
    )
```
Writing a lambda inside a lambda like this can be hard to read, and you need to make sure
that your parentheses are in the right places, and not for example:

```python
def get_full_name() -> Maybe[str]:
    return get_first_name().and_then(
        lambda first: get_last_name()
    ).and_then(
        lambda last: return Just(first + ' ' + last)
    )
```
Of course, if you use `mypy` it will warn you that `first` is not in scope in the last lambda, but
it would still be nice if we could make this a little easier to read.

The solution to this problem in other languages is syntactic sugar that will call `and_then` for you
behind the scenes, and let you work with the 'unwrapped' monadic value directly. In Haskell for example,
this is called `do` notation.

We can achieve something similar in python using generators, which is what the `with_effect` decorator
does for you:

```python
from pfun.maybe import with_effect, Maybes

@with_effect
def get_full_name() -> Maybes[str, str]:
    first = yield get_first_name()
    last = yield get_last_name()
    return first + ' ' + last
```
The `Maybes[A, B]` type is just a type alias for `Generator[Maybe[A], A, B]`.

You may want to unwrap monadic values of heterogenous types inside a `with_effect` decorated function. However,
the `Generator` type does not allow us to express that our function wants to receive, say first
an `int` and then a `str`. So the best you can do is to add the types explicitly:

```python
from typing import Any

@with_effect
def heterogenous_yield_types() -> Maybes[Any, str]:
    an_int = yield Just(1)  # type: int
    a_str = yield Just('an_int was: ')  # type: str
    return str(a_str) + an_int
```

Some monads have a "failure" value, such as `Maybe` (`Nothing`), `Either` (`Left`) and `Result` (`Error`). You may want to terminate
the computation inside a `with_effect` decorated function under some conditions using the failure value. This can be done like:
```python

@with_effect
def divide(a: int, b: int) -> Maybes[Any, float]:
    if b == 0:
        yield Nothing()
    return a / b
```
This works because if `b == 0`, a `Nothing` is yielded and control-flow is returned to the `with_effect` decorator. `with_effect` will then bind the rest of the function together
with the `Nothing`, in effect:

```python
generator = divide(a, b)
maybe = next(generator)
maybe.and_then(lambda v: generator.send(v))
... # with_effect then consumes any remaining yields, and finally wraps
    # the return value in a "Just"
```
## Stack-Safety and Recursion
Its common to use recursion rather than looping in pure functional programming to avoid mutating a local variable.

Consider e.g the following implementation of the factorial function:

```python
def factorial(n: int) -> int:
    if n == 1:
        return 1
    return n * factorial(n - 1)
```
Called with a large enough value for `n`, the recursive calls will overflow the python stack.

A common solution to this problem in other languages that perform tail-call-optimization is to rewrite the function
to put the recursive call in tail-call position.

```python
def factorial(n: int) -> int:
    
    def factorial_acc(n: int, acc: int) -> int:
        if n == 1:
            return acc
        return factorial_acc(n - 1; n * acc)
        
    return factorial_acc(n, 1)
```
In Python however, this is not enough to solve the problem because Python does not perform tail-call-optimization.

In languages without tail-call-optimization such as Python, its common to use a data structure called a trampoline
to wrap the recursive calls into objects that can be interpreted in constant stack space, by letting the function
return immediately at each recursive step.

```python
from pfun.trampoline import Trampoline, Done, Call


def factorial(n: int) -> int:
    
    def factorial_acc(n: int, acc: int) -> Trampoline[int]:
        if n == 1:
            return Done(acc)
        return Call(lambda: factorial_acc(n - 1, n * acc))

    return factorial_acc(n, 1).run()
```
However note that in most cases a recursive function can be rewritten into an iterative one
that looks completely pure to the caller because it only mutates local variables:

```python
def factorial(n: int) -> int:
    acc = 1
    for i in range(1, n + 1):
        acc *= i
    return acc
```
This is the recommended
way of solving recursive problems (when it doesn't break [referential transparency](https://en.wikipedia.org/wiki/Referential_transparency)), because it avoids overflowing the stack, and
is often easier to understand.

Sometimes you'll find yourself in a situation where you want to write a recursive monadic function.
For some monads this is not a problem since they are designed to be stack safe (`Reader`, `State`, `IO`, and `Cont`).
But for other monads (`Maybe`, `Either` and `Writer`), this can lead to `RecursionError`. Consider `pow_writer` which computes integer powers by recursion:

```python
from pfun.writer import value, tell

def pow_writer(n: int, m: int) -> Writer[None, int]:
    if m == 0:
        return value(None)
    return tell(n).and_then(lambda _: pow_writer(n, m - 1))
```

`pow_writer` cannot easily be trampolined because the function passed to `and_then` which performs the recursion 
must return a `Writer`, and not a `Trampoline`.

In these cases the helper function `tail_rec` is provided which can help you trampoline you monadic function using `Either`:
```python
from pfun.either import Either, Left, Right
from typing import Tuple

def pow_writer(n: int, m: int) -> Writer[Either[Tuple[int, int], None], int]:
    def _(n_m):
        n, m = n_m
        if m == 0:
            return value(None).map(Right)
        return tell(n).and_then(lambda _: value((n, m - 1))).map(Left)
    return tail_rec(_, (n, m))
```

(Of course also in this example there are several ways of computing the same thing that does not
rely on recursion and does not break referential transparency.)
