# Programming Guide
This section gives you an overview over functional programming and
static type checking with `pfun`. This is a good place to start, especially if you're new to programming in monadic style.
For a detailed documentation of all classes and functions, see [API Reference](api_reference.html).
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
to see that this function can fail from the type signature alone (and hence also no way for your favourite PEP 484 type-checker).

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
chain together effectul functions that keeps track of the effects along the way automatically
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

### Result
`Maybe` allowed us to put the failure effect in the type signature, but
it doesn't tell the caller _what_ went wrong. `Result` will do that:

```python
from pfun.result import Result, Ok, Error


def i_can_fail(s: str) -> Result[str, ValueError]:
    if s == 'illegal value':
        return Error(ValueError())
    return Ok('Ok!')
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
def calls_f(conncetion: Connection) -> str:
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
Ok, lets break that down: `Reader[Context, Result]` is an object holding a function that
can take an object of type `Context` and produce a an object of type `Value`. So

```Reader(lambda c: do_something(c.get_data())): Reader[Connection, str]```

 means:
make a `Reader` object that when given a `Connection` object produces a `str` by calling `do_something`.

You can call `run` on a reader object to call the function it holds:

```python
connection = Connection('host:user:password')
data = connection.get_data()
assert do_something(data) == Reader(lambda c: do_something(c.get_data())).run(connection)
```

`value(v: Value): Reader[Any, Value]` is a function that simply makes a `Reader` object that returns `v` no matter the context.
In other words:

```python
value(1) == Reader(lambda _: 1)
```

This is useful for making monadic functions, such as `f`.


Finally `ask(): Reader[Context, Context]` is a function that simply returns the `Context`
that will eventually be given by a caller of run. In other words

```ask().run(1) == 1```

Phew, that was kind of a lot to take in. Is this really better than just passing the `Connection` instance around?
Well, notice that:

- `calls_f` doesn't mention the connection at all (except for in the type signature).
This may not seem like a big deal in this contrived example, but if `main`
and `f` were separated not by 1 but many functions, passing around the `Connection`
instance would be pretty tedious.
- `calls_f` has no way of modifying the `Connection` that gets passed around. Even if
`calls_f` tried to do all sorts of tricks by calling `ask`, the `Connection` instance that
is eventually passed to `f` is unchanged. In other words, your program is guaranteed to be
side-effect free.


### Writer
Imagine that you are logging by appending to a `tuple` (Why a `tuple`? Well because they're
immutable of course!). Trying to avoid global mutable state,
you decide to pass the list around as a common argument to all the functions
in your program that needs to do logging
```python
from typing import Tuple
def i_need_to_log_something(i: int, log: Tuple[str]) -> Tuple[int, Tuple[str]]:
    result = compute_something(i)
    log = log + ('Something was sucessfully computed',)
    return result, log
 
def i_need_to_log_something_too(i: int, log: Tuple[str]) -> Tuple[int, Tuple[str]]:
    result = compute_something_else(i)
    log = log + ('Something else was computed',)
    return result, log


def main():
    result, log = i_need_to_log_something(1, ())
    result, log = i_need_to_log_something_too(result, log)
    print('reseult', result)
    print('log', log)
```
Well that obviously works, but there is a lot of logistics involved that seems
like it should be possible to abstract. This is what `Writer` will do for you:

```python
from typing import List
from pfun.writer import value, Writer


def i_need_to_log_something(i: int) -> Writer[int, List[str]]:
    result = compute_something(i)
    return Writer(result, ['Something was succesfully computed'])
    
    
def i_need_to_log_something_too(i: int) -> Writer[int, List[str]]:
    result = compute_something_else(i)
    return Writer(result, ['Something else was succesfully computed'])


def main():
    _, log = i_need_to_log_something(1).and_then(i_need_to_log_something_too)
    print('log', log)  # output: ['Something was succesfully computed', 'Something else was successfully computed']
 
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
How do you make io operations referentially transparent? Is io not inherently stateful?

### Combining Unwrapped Values
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

We can achieve something similar in python using generators, which is what the `do` decorator
does for you:

```python
from pfun.maybe import do, Do

@do
def get_full_name() -> Do[str, str]:
    first = yield get_first_name()
    last = yield get_last_name()
    return first + ' ' + last
```
The `Do[A, B]` class is just a type alias for `Generator[Maybe[A], A, B]`.

You may want to unwrap monadic values of heterogenous types inside a `do` function. However,
the `Generator` type does not allow us to express that our function wants to receive, say first
an `int` and then a `str`. So the best you can do is to add the types explicitly:

```python
from typing import Any

@do
def heterogenous_do() -> Do[Any, str]:
    an_int = yield Just(1)  # type: int
    a_str = yield Just('an_int was: ')  # type: str
    return str(an_str) + an_int
```
## Immutable Objects and Data Structures
### List
`List` is a functional style wrapper around `list` that prevents mutation
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
`Dict` is a functional style wrapper around `dict` that prevents mutation.

```python
from pfun import Dict

d = Dict(key='value')
d2 = d.set('new_key', 'new_value')
assert 'new_key' not in d and d2['new_key'] == 'new_value'
```
### Immutable

`Immutable` is an abstract class to 
## Utilities
### compose
### curry


## MyPy Plugin


```
[mypy]
plugins = pfun.mypy_plugin
```