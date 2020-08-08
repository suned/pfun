In functional programming, programs are built by composing functions that have no [side-effects](https://en.wikipedia.org/wiki/Side_effect_(computer_science)). This means that problems that we normally solve using side-effects in imperative programming such as performing io or raising exceptions are solved differently. The `pfun.effect.Effect` type lets you express side-effects in a side-effect free fashion. Readers with functional programming experience may be familiar with the term "[functional effect system](https://en.wikipedia.org/wiki/Effect_system)", which is precisely what `pfun.effect.Effect` is.

## Effect
The core type you will use when expressing side-effects with `pfun` is `pfun.effect.Effect`. `Effect` has a function `run` that perfoms the side-effect it represents. `run` is a function that:

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
    def run(self, r: R) -> A:
        """
        May raise E
        """
        ...
```
In other words, `Effect` takes three type paramaters: `R`, `E` and `A`. We'll study them one at a time.

### The Success Type
The `A` in `Effect[R, E, A]` is the _success type_. This is the type that the effect function will return if no error occurs. For example, in an `Effect` instance that reads a file as a `str`, `A` would be parameterized with `str`. You can create an `Effect` instance that succeeds with the value `a` using `pfun.effect.success(a)`:

```python
from typing import NoReturn
from pfun.effect import success, Effect


e: Effect[object, NoReturn, str] = success('Success!')
assert e.run(None) == 'Success!'
```
(You don't actually have to write the type of `e` explicitly, as it can be inferred by your type checker. We do it here simply because it's instructive to look at the types). Don't worry about the meaning of `object` and `NoReturn` for now, we'll explain that later. For now, just understand that when `e` has the type `Effect[object, NoReturn, str]`, it means that when you call `e.run` with any parameter, it will return a `str` (the value `Success!`).

You can work with the success value of an effect using instance methods of `Effect`. If you want to transform the result of an `Effect` with a function without side-effects you can use `map`, which takes a function of the type `Callable[[A], B]` as an argument, where `A` is the success type of your effect:

```python
e: Effect[object, NoReturn, str] = success(1).map(str)
assert e.run(None) == "1"
```

If you want to transform the result of an `Effect` with a function that produces other side effects (that is, returns an `Effect` instance), you use `and_then`:
```python
add_1 = lambda v: success(v + 1)
e: Effect[object, NoReturn, int] = success(1).and_then(add_1)
assert e.run(None) == 2
```
(for those with previous functional programming experince, `and_then` is the "bind" operation of `Effect`).


### The Error Type
The `E` in `Effect[R, E, A]` is the _error type_. This is type that the `run` function will raise if it fails. You can create an effect that does nothing but fail using `pfun.effect.error`:

```python
from typing import NoReturn

from pfun.effect import Effect, error


e: Effect[object, str, NoReturn] = error('Whoops!')
e.run(None)  # raises: RuntimeError('Whoops!')
```

For a concrete example, take a look at the `pfun.files` module that helps you read from files:

```python
from pfun.effect import Effect
from pfun.files import Files


files = Files()
e: Effect[object, OSError, str] = files.read('doesnt_exist.txt')
e.run(None)  # raises OSError
```
Don't worry about the api of `files` for now, simply notice that when `e` has the type `Effect[object, OSError, str]`, it means that when you execute `e` it can produce a `str` or fail with `OSError`. Having the the error type explicitly modelled in the type signature of `e` allows type safe error handling as we'll see later.

### The Dependency Type
Finally, let's look at `R` in `Effect[R, E, A]`: the _dependency type_. `R` is the argument that `run` requires to produce its result. It allows you to parameterize the side-effect that your `Effect` implements which improves re-useability and testability. For example, imagine that you want to use `Effect` to model the side-effect of reading from a database. The function that reads from the database requires a connection string as an argument to connect. If `Effect` did not take a parameter you would have to pass around the connection string as a parameter through function calls, all the way down to where the connection string was needed.

The dependency type allows you to pass in the connection string at the edge of your program, rather than threading it through a potentially deep stack of function calls:

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
    program.run('user@prod_db')

    # run in development
    program.run('user@dev_db')
```
In the next section, we will discuss this _dependency injection_ capability of `Effect` in detail.

## The Module Pattern
This section is dedicated to the dependency type `R`. In most examples we have looked at so far, `R` is parameterized with `object`. This means that it can safely be called with any value (since all Python values are sub-types of `object`). This is mostly useful when you're working with effects that don't use the dependency argument for anything, in which case any value will do.

In the previous section we saw how the `R` parameter of `Effect` can be used for dependency injection. But what happens when we try to combine two effects with different dependency types with `and_then`? The `Effect` instance returned by `and_then` must have a dependency type that is a combination of the dependency types of both the combined effects, since the dependency passed to the combined effect is also passed to the other effects.

Consider for example this effect, that uses the `execute` function from above to get database results, and combines it with a function `make_request` that calls an api, and requires a `Credentials` instance as the dependency type:

```python
class Credentials:
    ...


def make_request(results: List[DBRow]) -> Effect[Credentials, HTTPError, bytes]:
    ...

results: effect.Effect[str, IOError, List[DBRow]] = execute('select * from users;')
response: effect.Effect[..., Union[IOError, HTTPError], HTTPResponse]
response = results.and_then(make_request)
response.run(...)  # What could this argument be?
```
To call the `response.run` function, we need an instance of a type that is a `str` and a `Credentials` instance _at the same time_, because that argument must be passed to both the effect returned by `execute` and by `make_request`. Ideally, we want `response` to have the type `Effect[Intersection[Credentials, str], IOError, bytes]`, where `Intersection[Credentials, str]` indicates that the dependency type must be both of type `Credentials` and of type `str`.

In theory such an object could exist (defined as `class MyEnv(Credentials, str): ...`), but there are no straight-forward way of expressing that type dynamically in the Python type system. As a consequence, `pfun` infers the resulting effect with the `R` parameterized as `typing.Any`, which in this case means that `pfun` could not assign a meaningful type to `R`.

If you use the `pfun` MyPy plugin, you can however redesign the program to follow a pattern that enables `pfun` to infer a meaningful combined type
in much the same way that the error type resulting from combining two effects using `and_then` can be inferred. This pattern is called _the module pattern_.

In its most basic form, the module pattern simply involves defining a [Protocol](https://docs.python.org/3/library/typing.html#typing.Protocol) that serves as the dependency type of an `Effect`. `pfun` can combine dependency types of two effects whose dependency types are both protocols, because the combined dependency type is simply a new protocol that inherits from both. This combined protocol is called `pfun.Intersection`.

In many cases the api for effects involved in the module pattern is split into three parts:

- A _module_ class that provides the actual implementation
- A _module provider_ that is a `typing.Protocol` that provides the module class as an attribute
- Functions that return effects with the module provider class as the dependency type.

Lets rewrite our example from before to follow the module pattern:
```python
from typing import Protocol
from http.client import HTTPError

from pfun.effect import Effect, depend


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
    Function that returns an effect with the HasRequest module provider as the dependency type
    """
    return depend(HasRequests).and_then(lambda env: env.requests.make_request(results))


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
    Function that returns an effect with the HasDatabase module provider as the dependency type
    """
    return depend(HasDatabase).and_then(lambda env: env.database.execute(query))
```
There are two _modules_: `Requests` and `Database` that provide implementations. There are two corresponding _module providers_: `HasRequests` and `HasDatabase`. Finally there are two functions `execute` and `make_request` that puts it all together.

Pay attention to the fact that `execute` and `make_request` look quite similar: they both start by calling `pfun.effect.depend`. This function returns an effect that succeeds with the dependency value that will eventually be passed as the argument to the final effect (in this example the effect produced by `execute(...).and_then(make_request)`). The optional parameter passed to `depend` is merely for type-checking purposes, and doesn't change the result in any way.

If we combine the new functions `execute` and `make_request` that both has protocols as the dependency types, `pfun` can infer a meaningful type, and make sure that the dependency type that is eventually passed to the whole program provides both the `requests` and the `database` attributes:

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

Quite a mouthful, but what it tells us is that `effect` must be run with an instance of a type that has both the `requests` and `database` attributes with appropriate types. In other words, if you accidentally defined your dependency as:
```python
class Env:
    database = Database('user@prod_db')


effect.run(Env())
```
MyPy would tell you the call `effect.run(Env())` is a type error since `Env` doesn't have a `requests` attribute. It's worth understanding the module pattern, since `pfun` uses it pervasively in its api, e.g in `pfun.files` and `pfun.console`, in order that `pfun` can infer the dependency type of effects resulting from combining functions from `pfun` with user defined functions that also follow the module pattern.

A very attractive added bonus of the module pattern is that mocking out particular dependencies of your program becomes extremely simple, and by extension that unit testing becomes easier:
```python
from pfun.effect import success
from unittest.mock import Mock


mock_env = Mock()
mock_env.requests.make_request.return_value = success(b'Mocked!')

assert make_request([])(mock_env) == b'Mocked!'
```


## Error Handling
In this section, we'll look at how to handle errors of effects with type safety. In previous sections we have already spent some time looking at the `Effect` error type. In many of the examples so far, the error type was `typing.NoReturn`. An `Effect` with this error type can never return a value for an error, or in other words, it can never fail (as those effects returned by `pfun.effect.success`). In the rest of this section we'll of course be pre-occupied with effects that _can_ fail.

When you combine side effects using `Effect.and_then`, `pfun` uses `typing.Union` to combine error types, in order that the resulting effect captures all potential errors in its error type:
```python
from typing import List

from pfun.files import Files


def parse(content: str) -> effect.Effect[object, ZeroDivisionError, List[int]]:
    ...


files = Files()
e: Effect[object, Union[OSError, ZeroDivisionError], List[int]]
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
from pfun.effect import success, error, Effect


def handle_errors(reason: Union[OSError, ZeroDivisionError]) -> Effect[object, ZeroDivisionError, str]:
    if isinstance(reason, OSError):
        return success('default value)
    return error(reason)


recovered: Effect[object, ZeroDivisionError, str] = e.recover(handle_errors)
```

You will frequently handle errors by using `isinstance` to compare errors with types, so defining your own error types becomes even more important when using `pfun` to distinguish one error source from another.

## Concurrency
`Effect` uses `asyncio` under the hood to run effects asynchronously.
This can lead to significant speed ups.

Consider for example this program that calls `curl http://www.google.com` in a subprocess 50 times:
```python
# call_google_sync.py
import timeit
import subprocess


[subprocess.run(['curl', 'http://www.google.com']) for _ in range(50)]
```
Timing the execution using the unix `time` informs me this takes 5.15 seconds on a normal consumer laptop. Compare this to the program below which does more or less the same thing, but using `pfun.subprocess`:

```python
# call_google_async.py
from pfun.subprocess import Subprocess
from pfun.effect import sequence_async


sp = Subprocess()
effect = sequence_async(sp.run_in_shell('curl http://www.google.com') for _ in range(50)
effect.run(None)
```

This program finishes in 0.78 seconds, according to `time`. The crucial difference is the function `pfun.effect.sequence_async` which returns a new effect that runs its argument effects asynchronously using `asyncio`. This means that one effect can yield to other effects while waiting for input from the `curl` subprocess. This ultimately saves a lot of time compared to the synchronous implementation where each call to `subprocess.run` can only start when the preceeding one has returned.

You can create an effect from a Python awaitable using `pfun.effect.from_awaitable`, allowing you to integrate with `asyncio` directly in your own code:
```python
import asyncio
from typing import Any, NoReturn
from pfun.effect import from_awaitable, Effect


async def sleep() -> str:
    await asyncio.sleep(1)
    return 'success!'


e: Effect[object, NoReturn, str] = from_awaitable(sleep())
assert e.run(None) == 'success!'
```

You can also pass `async` functions directly to `map` and `and_then`:
```python
from typing import Any, NoReturn
import asyncio

from pfun.effect import success


async def sleep_and_add_1(a: int) -> int:
    await asyncio.sleep(1)
    return a + 1


assert success(1).map(sleep_and_add_1).run(None) == 2
```

When using `pfun` with async frameworks such as [ASGI web servers](https://asgi.readthedocs.io/en/latest/), you can await the the result of effects using `Effect.__call__` (which is really what `Effect.run` calls using the supplied event-loop):

```python
async def f() -> str:
    e: Effect[object, NoReturn, str] = ...
    return await e(None)
```

Since `Effect` uses `asyncio` you should be careful not to create effects that block the main thread. Blocking happens in two ways:

- Performing IO
- Calling functions that take a long time to return

To avoid blocking the main thread, synchronous IO should be performed in a separate thread, and CPU bound functions should be called in a separate process. `pfun.effect` does this automatically with functions passed to its api when they are decorated with `pfun.effect.io_bound` or `pfun.effect.cpu_bound`:
```python
import time

from pfun.effect import success, cpu_bound, io_bound


def slow_function(a: int) -> int:
    # simulate doing something slow
    time.sleep(2)
    return a + 2


def performs_io(a: int) -> None:
    with open('foo.txt', 'w') as f:
        f.write(str(a))

success(2).map(cpu_bound(slow_function))
success(2).map(io_bound(performs_io))
```
`io_bound` and `cpu_bound` can be used to decorate functions that are used
as arguments anywhere in the `pfun.effect` api. However, the decorator must directly wrap the function passed to the api in order for `pfun` to recognize that the function should be called in a separate process or thread. In other words, this won't work:
```python
decorated = cpu_bound(slow_function)
success(2).map(lambda v: decorated(v))
```

## Purely Functional State
Mutating non-local state is a side-effect that we want to avoid when doing functional programming. This means that we need a mechanism for managing state as an effect. `pfun.ref` provides exactly this. `pfun.ref` works by mutating state only by calling `Effect` instances.

```python
from typing import Tuple, Any, NoReturn

from pfun.ref import Ref
from pfun.effect import Effect


ref: Ref[Tuple[int, ...]] = Ref(())
add_1: Effect[object, NoReturn, None] = ref.modify(lambda old: return old + (1,))
# calling modify doesn't modify the state directly
assert ref.value == ()
# The state is modified only when the effect is called
add_1.run(None)
assert ref.value == (1,)
```
`pfun.ref.Ref` protects access to the state using an `asyncio.Lock`, meaning that updating the state can be done atomically with the following methods:

- `Ref.get()` read the current value of the state
- `Ref.set(new_state)` update the state to `new_value` atomically, meaning no other effect can read the value of the state while the update is in progress. Note that if you first read the state using `Ref.get` and then set it with `Ref.set`, other effects may read the value in between which may lead to lost updates. _For this use case you should use `modify` or `try_modify`_
- `Ref.modify(update_function)` read and update the state with `update_function` atomically, meaning no other effect can read or write the state before the effect produced by `modify` returns
- `Ref.try_modify(update_function)` read and update the state with `update_function` atomically, if `update_funciton` succeeds. Success is signaled by the `update_function` by returning a `pfun.either.Right` instance, and error by returning a `pfun.either.Left` instance.

`pfun.ref` can of course be combined with the module pattern:
```python
from typing import Tuple, Any, NoReturn, Protocol

from pfun.ref import Ref
from pfun.effect import depend, Effect


class HasState(Protocol):
    state: Ref[Tuple[int, ...]]


def set_state(state: Tuple[int, ...]) -> Effect[HasState, NoReturn, None]:
    return depend().and_then(lambda env.state.set(state))
```
## Creating Your Own Effects
`pfun.effect` has a number of decorators and helper functions to help you create
your own effects.

`pfun.effect.from_callable` is the most flexible option. It takes a function
that takes a dependency type and returns a `pfun.either.Either` and turns it into an effect:
```python
from pfun.effect import from_callable, Effect
from pfun.either import Either


def f(r: str) -> Either[Exception, float]:
    ...


effect: Effect[str, Exception, float] = from_callable(f)
```
`from_callable` may also be used to create effects from async functions:
```python
import asyncio


async def f(r: str) -> Either[Exception, float]:
    await asyncio.sleep(1)
    ...


effect: Effect[str, Exception, float] = from_callable(f)
```

`pfun.effect.catch` is used to decorate functions
that may raise exceptions. If the decorated function performs side effects, they
are not carried out until the effect is run
```python
from pfun.effect import catch, Effect


@catch(ZeroDivisionError, ValueError)
def f(v: int) -> int:
    if v > 5:
        raise ValueError('v is not allowed to be > 5 for some reason')
    return 1 / v


effect: Effect[object, Union[ZeroDivisionError, ValueError], int] = f(0)
```

## Type Aliases
Since the dependency type of `Effect` is often parameterized with `object`, and the error type is often parameterized with `typing.NoReturn`, a number of type aliases for `Effect` are provided to save you from typing out `object` and `NoReturn` over and over. Specifically:

- `pfun.effect.Success[A]` is a type-alias for `Effect[object, typing.NoReturn, A]`, which is useful for effects that can't fail and doesn't have dependencies
- `pfun.effect.Try[E, A]` is a type-alias for `Effect[object, E, A]`, which is useful for effects that can fail but doesn't have dependencies
- `pfun.effect.Depends[R, A]` is a type-alias for `Effect[R, typing.NoReturn, A]` which is useful for effects that can't fail but needs dependency `R`

## Combining effects
Sometimes you need to keep the the result of two or more effects in scope to work with
both at the same time. This can lead to code like the following:
```python
from pfun.effect import success


two = success(2)

four = two.and_then(lambda a: lambda two.map(lambda b: a + b))
```
In these cases, consider using `pfun.effect.lift` or `pfun.effect.combine`.

`lift` is a decorator that enables any function to work with effects
```python
from pfun.effect import lift


def add(a: int, b: int) -> int:
    return a + b

four = lift(add)(two, two)
```
`combine` is like `lift` but with its arguments flipped:
```python
from pfun.effect import combine

four = combine(two, two)(add)
```
