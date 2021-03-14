`pfun` is a Python library that aims to make [functional programming](https://en.wikipedia.org/wiki/Functional_programming) in Python fun and easy. On its own, Python has all the features necessary to write code in functional style. However, many programmers find functional programming in Python difficult and tedious because it lacks features supporting common functional design patterns. `pfun` supplies the last few puzzle pieces that make functional programming in Python ergonomical. Specifically:

- `pfun` provides a simple, unified api for working with any side-effect in functional style through a full-fledged [functional effect system](https://en.wikipedia.org/wiki/Effect_system) that doesn't rely on complex solutions such as [monad transformers](https://en.wikipedia.org/wiki/Monad_transformer).
- Python doesn't perform [tail call optimization](https://en.wikipedia.org/wiki/Tail_call) which is a problem for many functional design patterns that rely on recursion. `pfun` solves this by building [trampolining](https://en.wikipedia.org/wiki/Trampoline_(computing)) into all relevant types and functions
- `pfun` provides immutable data structures with a functional api, as well as tools for building your own immutable data types.
- The Python type annotations are often too limited to accurately type common functional design patterns. `pfun` solves this by including a [MyPy](http://mypy-lang.org/) plugin that provides very precise typing.
- `pfun` integrates functional patterns for async programming with the `asyncio` module.

`pfun` differs from other libraries for functional Python programming in that

- `pfun` takes a modern approach to functional programming inspired by state of the art solutions to working with side-effects from functional programming languages (specifically the [Zio](https://zio.dev/) Scala libary)
- `pfun` was designed with a strong emphasis on static type checking
- `pfun` is designed to be "pythonic", using Python conventions and best practices when possible, favouring easy to understand names over functional programming jargon, and integrating with the Python standard library as much as possible.
