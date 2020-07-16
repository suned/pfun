# Guide
This section gives you an overview over functional programming and
static type checking with `pfun`. This is a good place to start, especially if you're new to functional programming.
For a detailed documentation of all classes and functions, see [API Reference](api_reference.html).

## Install

`pip install pfun`

## MyPy Plugin

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
assert List(range(3)).reduce(lambda a, b: a + b) == 3
assert List(range(3)).map(str) == ['0', '1', '2']
```
### Dict
`Dict` is a functional style dictionary.

```python
from pfun import Dict, maybe

d = Dict({'key': 'value'})
d2 = d.set('new_key', 'new_value')
assert 'new_key' not in d and d2.get('new_key') == maybe.Just('new_value')
```

It supports the same api as `dict` which the exception of `__setitem__` which will raise an exception, and uses
`pfun.maybe.Maybe` to indicate the presence or absence of a key when using `get`.

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
In functional programming, programs are built by composing functions that have no side-effects. This means that things that we normally model as side-effects in imperative programming such as performing io or raising exceptions are modelled differently. The best way to deal with side-effecty things such as io or error handling with `pfun` is to use the `pfun.effect` module, which lets you work with side-effecty stuff in a side-effect free fashion. Readers with functional programming experience may be familiar with the term "[functional effect system](https://en.wikipedia.org/wiki/Effect_system)", which is precisely what `pfun.effect` is.

### Effect
The core type you will use when expressing side-effects with `pfun` is `pfun.effect.Effect`. `Effect` is a callable that

- Takes exactly one argument
- May or may not perform side-effects when called (including raising exceptions)

You can think of `Effect` defined as:
```python
from typing import TypeVar, Generic
from pfun.either import Either


R = TypeVar('R', contravariant=True)
E = TypeVar('E', covariant=True)
A = TypeVar('A', covariant=True)


class Effect(Generic[R, E, A]):
    def __call__(self, r: R) -> A:
        """
        May raise E
        """
        ...
```
In other words, `Effect` takes three type paramaters: `R`, `E` and `A`. We'll study them one at a time.

#### The Success Type
The `A` in `Effect[R, E, A]` is the _success type_. This is the type that the effect function will return if no error occurs. For example, in an `Effect` instance that reads a file as a `str`, `A` would be parameterized with `str`. You can create an `Effect` instance that succeeds with the value `a` using `effect.success(a)`:

```python
from typing import Any, NoReturn
from pfun import success, Effect

e: Effect[object, NoReturn, str] = success('Success!')
assert e(None) == 'Success!'
```
(You don't actually have to write the type of `e` explicitly, as it can be inferred by your type checker. We do it here simply because it's instructive to look at the types). Don't worry about the meaning of `object` and `NoReturn` for now, we'll explain that later. For now, just understand that when `e` has the type `Effect[object, NoReturn, str]`, it means that when you call `e` with any parameter, it will return a `str` (the value `Success!`).

You can work with the success value of an effect using instance methods of `Effect`. If you want to transform the result of an `Effect` with a function without side-effects you can use `map`, which takes a function of the type `Callable[[A], B]` as an argument, where `A` is the success type of your effect:

```python
e: Effect[object, NoReturn, str] = success(1).map(str)
assert e(None) == "1"
```

If you want to transform the result of an `Effect` with a function that produces other side effects (that is, returns an `Effect` instance), you use `and_then`:
```python
add_1 = lambda v: success(v + 1)
e: Effect[Any, NoReturn, int] = success(1).and_then(add_1)
assert e(None) == 2
```
(for those with previous functional programming experince, `and_then` is the "bind" operation of `Effect`).


#### The Error Type
The `E` in `Effect[R, E, A]` is the _error type_. This is type that the effect function will raise if it fails. You can create an effect that does nothing but fail using `pfun.effect.error`:

```python
from typing import Any, NoReturn

from pfun import Effect, error


e: Effect[object, str, NoReturn] = error('Whoops!')
e(None)  # raises: RuntimeError('Whoops!')
```

For a concrete example, take a look at the `pfun.files` module that helps you read from files:

```python
from typing import Any

from pfun import Effect
from pfun.files import Files


files = Files()
e: Effect[object, OSError, str] = files.read('doesnt_exist.txt')
e(None)  # raises OSError
```
Don't worry about the api of `files` for now, simply notice that when `e` has the type `Effect[object, OSError, str]`, it means that when you execute `e` it can produce a `str` or fail with `OSError`. Having the the error type explicitly modelled in the type signature of `e` allows type safe error handling as we'll see later.

#### The Environment Type
Finally, let's look at `R` in `Effect[R, E, A]`: the _environment type_. `R` is the argument that your effect function requires to produce its result. It allows you to parameterize the side-effect that your `Effect` implements which improves re-useability and testability. For example, imagine that you want to use `Effect` to model the side-effect of reading from a database. The function that reads from the database requires a connection string as an argument to connect. If `Effect` did not take a parameter you would have to pass around the connection string as a parameter through function calls, all the way down to where the connection string was needed.

The environment type allows you to pass in the connection string at the edge of your program, rather than threading it through a potentially deep stack of function calls:

```python
from typing import List, Dict, Any


DBRow = Dict[Any, Any]


def execute(query: str) -> Effect[str, IOError, List[DBRow]]:
    ...

def find_row(results: List[DBRow]) -> DBRow:
    ...

def main() -> Effect[str, IOError, DBRow]:
    return execute('select * from users;').map(find_row)


if __name__ == '__main__':
    program = main()

    # run in production
    program('user@prod_db')

    # run in development
    program('user@dev_db')
```
In the next section, we will discuss this _dependency injection_ capability of `Effect` in detail.

#### The Module Pattern
This section is dedicated to the environment type `R`. In most examples we have looked at so far, `R` is parameterized with `object`. This means that it can safely be called with any value (since all Python values are sub-types of `object`). This is mostly useful when you're working with effects that don't use the environment argument for anything, in which case any value will do.

In the previous section we saw how the `R` parameter of `Effect` can be used for dependency injection. But what happens when we try to combine two effects with different environment types with `and_then`? The `Effect` instance returned by `and_then` must have an environment type that is a combination of the environment types of both the combined effects, since the environment passed to the combined effect is also passed to the two other effects. Consider for example this effect, that uses the `execute` function from above to get database results, and combines it with a function `make_request` that calls an api, and requires a `Credentials` instance as the environment type:

```python
class Credentials:
    ...


def make_request(results: List[DBRow]) -> Effect[Credentials, HTTPError, bytes]:
    ...

results: effect.Effect[str, IOError, List[DBRow]] = execute('select * from users;')
response: effect.Effect[..., Union[IOError, HTTPError], HTTPResponse]
response = results.and_then(make_request)
response(...)  # What could this argument be?
```
To call the `response` function, we need an instance of a type that is a `str` and a `Credentials` instance _at the same time_, because that argument must be passed to both the effect returned by `execute` and by `make_request`. Ideally, we want `response` to have the type `Effect[Intersection[Credentials, str], IOError, bytes]`, where `Intersection[Credentials, str]` indicates that the environment type must be both of type `Credentials` and of type `str`.

In theory such an object could exist (defined as `class MyEnv(Credentials, str): ...`), but there are no straight-forward way of expressing that
type dynamically in the Python type system. As a consequence, `pfun` infers the resulting effect with the `R` parameterized as `typing.Any`, which in this case means that `pfun` could not assign a meaningful type to `R`.

If you use the `pfun` MyPy plugin, you can however redesign the program to follow a pattern that enables `pfun` to infer a meaningful combined type
in much the same way that the error type resulting from combining two effects using `and_then` can be inferred. This pattern is called _the module pattern_.

In its most basic form, the module pattern simply involves defining a [Protocol](https://docs.python.org/3/library/typing.html#typing.Protocol) that serves as the environment type of an `Effect`. `pfun` can combine environment types of two effects whose environment types are both protocols, because the combined environment type is simply a new protocol that inherits from both. This combined protocol is called `pfun.effect.Intersection`.

In many cases the api for effects involved in the module pattern is split into three parts:

- A _module_ class that provides the actual implementation
- A _module provider_ that is a `typing.Protocol` that provides the module class as an attribute
- Functions that return effects with the module provider class as the environment type.

Lets rewrite our example from before to follow the module pattern:
```python
from typing import Any, Protocol
from http.client import HTTPError

from pfun.effect import Effect, get_environment

class Requests:
    """
    Requests implementation module
    """
    def __init__(self, credentials: Credentials):
        self.credentials = credentials

    def make_request(self, results: List[DBRow]) -> Effect[object, HTTPError, bytes]:
        ...


class HasRequests(Protocol):
    """
    Module provider class for the requests module
    """
    requests: Requests


def make_request(results: List[DBRow]) -> Effect[HasRequests, HTTPError, bytes]:
    """
    Function that returns an effect with the HasRequest module provider as the environment type
    """
    return get_environment(HasRequests).and_then(lambda env: env.requests.make_request(results))


class Database:
    """
    Database implementation module
    """
    def __init__(self, connection_str: str):
        self.connection_str = connection_str

    def execute(self, query: str) -> Effect[object, IOError, List[DBRow]]:
        ...


class HasDatabase(Protocol):
    """
    Module provider class for the database module
    """
    database: Database


def execute(query: str) -> Effect[HasDatabase, IOError, List[DBRow]]:
    """
    Function that returns an effect with the HasDatabase module provider as the environment type
    """
    return get_environment(HasDatabase).and_then(lambda env: env.database.execute(query))
```
There are two _modules_: `Requests` and `Database` that provide implementations. There are two corresponding _module providers_: `HasRequests` and `HasDatabase`. Finally there are two functions `execute` and `make_request` that puts it all together.

Pay attention to the fact that `execute` and `make_request` look quite similar: they both start by calling `pfun.effect.get_environment`. This function returns an effect that succeeds with the environment value that will eventually be passed as the argument to the final effect (in this example the effect produced by `execute(...).and_then(make_request)`). The optional parameter passed to `get_environment` is merely for type-checking purposes, and doesn't change the result in any way.

If we combine the new functions `execute` and `make_request` that both has protocols as the environment types, `pfun` can infer a meaningful type, and make sure that the environment type that is eventually passed to the whole program provides both the `requests` and the `database` attributes:

```python
effect = execute('select * from users;').and_then(make_request)
```
The type of `effect` in this case will be
```python
Effect[
    pfun.Intersection[HasRequests, HasDatabase],
    Union[HTTPError, IOError],
    bytes
]
```

Quite a mouthful, but what it tells us is that `effect` must be called with an instance of a type that has both the `requests` and `database` attributes with appropriate types. In other words, if you accidentally defined your environment as:
```python
class Env:
    database = Database('user@prod_db')


effect(Env())
```
MyPy would tell you the call `effect(Env())` is a type error since `Env` does not have a `requests` attribute. It's worth understanding the module pattern, since `pfun` uses it pervasively in its api, e.g in `pfun.effect.files` and `pfun.effect.console`, in order that `pfun` can infer the environment type of effects resulting from combining functions from `pfun` with user defined functions that also follow the module pattern.

A very attractive added bonus of the module pattern is that mocking out particular dependencies of your program becomes extremely simple, and by extension that unit testing becomes easier:
```python
from pfun.effect import success
from unittest.mock import Mock


mock_env = Mock()
mock_env.requests.make_request.return_value = success(b'Mocked!')

assert make_request([])(mock_env) == b'Mocked!'
```


#### Error Handling
In this section, we'll look at how to handle errors of effects with type safety. In previous sections we have already spent some time looking at the `Effect` error type. In many of the examples so far, the error type was `typing.NoReturn`. An `Effect` with this error type can never return a value for an error, or in other words, it can never fail (as those effects returned by `pfun.effect.success`). In the rest of this section we'll of course be pre-occupied with effects that _can_ fail.

When you combine side effects using `Effect.and_then`, `pfun` uses `typing.Union` to combine error types, in order that the resulting effect captures all potential errors in its error type:
```python
from typing import List

from pfun.effect.files import Files


def parse(content: str) -> effect.Effect[object, ZeroDivisionError, List[int]]:
    ...


files = Files()
e: effect.Effect[object, Union[OSError, ZeroDivisionError], List[int]]
e = files.read('foo.txt').and_then(parse)
```
`e` has `Union[OSError, ZeroDivisionError]` as its error type because it can fail if `files.read` fails, _or_ if `parse` fails. This compositional aspect of the error type of `Effect` means that accurate and complex error types are built up from combining simple error types. Moreover, it makes reasoning about error handling easy because errors disappear from the type when they are handled, as we shall see next.

The most low level function you can use to handle errors is `Effect.either`, which surfaces any errors that may have occurred as a `pfun.either.Either`, where a `pfun.either.Right` signifies a successful computation and a `pfun.either.Left` a failed computation:
```python
from typing import NoReturn
from pfun.effect import Effect, files
from pfun.either import Either, Left


# files.read can fail with OSError
may_have_failed: Effect[files.HasFiles, OSError, str] = files.read('foo.txt')
# calling either() surfaces the OSError in the success type as a pfun.either.Either
as_either: Effect[files.HasFiles, NoReturn, Either[OSError, str]] = may_have_failed.either()
# we can use map or and_then to handle the error
cant_fail: Effect[files.HasFiles, NoReturn, str] = as_either.map(lambda either: 'backup content' if isinstance(either, Left) else either.get)
```

Once you've handled whatever errors you want, you can push the error back into error type of the effect using `pfun.effect.absolve`:
```python
from typing import Any, NoReturn, List
from pfun.effect import Effect, absolve, files
from pfun.either import Either


# function to handle error
def handle(either: Either[Union[OSError, ZeroDivisionError], str]) -> Either[ZeroDivisionError, str]:
    ...

# define an effect that can fail
e: Effect[Any, Union[OSError, ZeroDivisionError], List[int]] = files.read('foo.txt').and_then(parse)
# handle errors using e.either.map
without_os_error: Effect[object, NoReturn, Either[OSError, str]] = e.either().map(handle)
# push the remaining error into the error type using absolve
e2: Effect[object, OSError, str] = absolve(without_os_error)
```

At a slightly higher level, you can use `Effect.recover`, which takes a function that can inspect the error and handle it.
```python
from typing import Any, Union
from pfun.effect import success, failure, Effect


def handle_errors(error: Union[OSError, ZeroDivisionError]) -> Effect[object, ZeroDivisionError, str]:
    if isinstance(error, OSError):
        return success('default value)
    return failure(error)

e: Effect[object, Union[OSError, ZeroDivisionError], str]
recovered: Effect[object, ZeroDivisionError, str] = e.recover(handle_errors)
```

You will frequently handle errors by using `isinstance` to compare errors with types, so defining your own error types becomes even more important when using `pfun` to distinguish one error source from another.

#### Asynchronous IO
`Effect` uses `asyncio` under the hood to run io bound side-effects asynchronously when possible.
This can lead to significant speed ups when an effect spends alot of time waiting for io.

Consider for example this program that calls `curl http://www.google.com` in a subprocess 50 times:
```python
# call_google_sync.py
import timeit
import subprocess

[subprocess.run(['curl', 'http://www.google.com']) for _ in range(50)]
```
Timing the execution using the unix `time` informs me this takes 5.15 seconds on my computer. Compare this to the program below which does more or less the same thing, but using `pfun.effect.subprocess`:

```python
# call_google_async.py
from pfun.effect.subprocess import Subprocess
from pfun.effect import sequence_async


sp = Subprocess()
effect = sequence_async(sp.run_in_shell('curl http://www.google.com') for _ in range(50)
effect(None)
```

This program finishes in 0.78 seconds, according to `time`. The crucial difference is the function `pfun.effect.sequence_async` which returns a new effect that runs its argument effects asynchronously using `asyncio`. This means that one effect can yield to other effects while waiting for input from the `curl` subprocess. This ultimately saves a lot of time compared to the synchronous implementation where each call to `subprocess.run` can only start when the preceeding one has returned. Functions that combine several effects such as `pfun.effect.filter_m` or `pfun.effect.map_m` generally run effects asynchronously, meaning you don't have to think too much about it.

You can create an effect from a Python awaitable using `pfun.effect.from_awaitable`, allowing you to integrate with `asyncio` directly in your own code:
```python
import asyncio
from typing import Any, NoReturn
from pfun.effect import from_awaitable, Effect


async def sleep() -> str:
    await asyncio.sleep(1)
    return 'success!'


e: Effect[object, NoReturn, str] = effect.from_awaitable(sleep())
assert e(None) == 'success!'
```

You can also pass `async` functions directly to `map` and `and_then`:
```python
from typing import Any, NoReturn
import asyncio

from pfun.effect import success


async def sleep_and_add_1(a: int) -> int:
    await asyncio.sleep(1)
    return a + 1


assert success(1).map(sleep_and_add_1)(None) == 2
```

#### Purely Functional State
Mutating non-local state is a side-effect that we want to avoid when doing functional programming. This means that we need a mechanism for managing state as an effect. `pfun.effect.ref` provides exactly this. `pfun.effect.ref` works by mutating state only by calling `Effect` instances.

```python
from typing import Tuple, Any, NoReturn

from pfun.effect.ref import Ref
from pfun.effect import Effect


ref: Ref[Tuple[int, ...]] = Ref(())
add_1: Effect[object, NoReturn, None] = ref.modify(lambda old: return old + (1,))
# calling modify doesn't modify the state directly
assert ref.value == ()
# The state is modified only when the effect is called
add_1(None)
assert ref.value == (1,)
```
`pfun.effect.ref.Ref` protects access to the state using an `asyncio.Lock`, meaning that updating the state can be done atomically with the following methods:
- `Ref.get()` read the current value of the state
- `Ref.set(new_state)` update the state to `new_value` atomically, meaning no other effect can read the value of the state while the update is in progress. Note that if you first read the state using `Ref.get` and then set it with `Ref.set`, other effects may read the value in between which may lead to lost updates. _For this use case you should use `modify` or `try_modify`_
- `Ref.modify(update_function)` read and update the state with `update_function` atomically, meaning no other effect can read or write the state before the effect produced by `modify` returns
- `Ref.try_modify(update_function)` read and update the state with `update_function` atomically, if `update_funciton` succeeds. Success is signaled by the `update_function` by returning a `pfun.either.Right` instance, and error by returning a `pfun.either.Left` instance.

`pfun.effect.ref` can of course be combined with the module pattern:
```python
from typing import Tuple, Any, NoReturn, Protocol

from pfun.effect.ref import Ref
from pfun.effect import get_environment, Effect


class HasState(Protocol):
    state: Ref[Tuple[int, ...]]


def set_state(state: Tuple[int, ...]) -> Effect[HasState, NoReturn, None]:
    return get_environment().and_then(lambda env.state.set(state))
```
### Type Aliases
Since the environment type of `Effect` is often parameterized with `object`, and the error type is often parameterized with `typing.NoReturn`, a number of type aliases for `Effect` are provided to save you typing out `object` and `NoReturn` over and over. Specifically:


```python
from typing import TypeVar, NoReturn

R = TypeVar('R')
E = TypeVar('E')
A = TypeVar('A')

# IO is for effects that can't fail and doesn't take an environment
IO = Effect[object, NoReturn, A]

# TryIO is for effects that can fail but doesn't take an environment
TryIO = Effect[object, E, A]

# Depends is for effects that can't fail but takes R as environment type
Depends = Effect[R, NoReturn, A]
```

#### Maybe
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

#### Either
`Maybe` allowed us to put the failure effect in the type signature, but
it doesn't tell the caller _what_ went wrong. `Either` will do that:

```python
from pfun.Either import Right, Left, Either


def i_can_fail(s: str) -> Either[ValueError, str]:
    if s == 'illegal value':
        return Left(ValueError())
    return Right('Ok!')
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
        return factorial_acc(n - 1, n * acc)

    return factorial_acc(n, 1)
```
In Python however, this is not enough to solve the problem because Python does not perform tail-call-optimization.

Because Python doesn't optimize tail calls, we need to use a data structure called a trampoline
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
