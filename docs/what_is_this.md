`pfun` is a Python library that aims to make [functional programming](https://en.wikipedia.org/wiki/Functional_programming) in Python fun and easy. On its own, Python has all the ingredients required to write functional code. `pfun` supplies the last few puzzle pieces that make functional programming in Python ergonomical. Specifically:

- Python doesn't perform tail call optimization, which is a problem for many functional design patterns. `pfun` solves this by building trampolining into all relevant types and functions
- `pfun` provides immutable data structures with a functional api, as well as tools for building your own immutable data types.
- `pfun` provides a full fledged functional effect system for working with side-effects in a side-effect-free fashion.
- The Python type annotations are often too limited to accurately type common functional design patterns. `pfun` solves this by including a MyPy plugin that provides very precise typing.
- `pfun` integrates functional patterns for async programming with `asyncio`

`pfun` differs from other libraries for functional Python programming in that

- It was designed with a strong emphasis on static type checking
- It is designed to be "pythonic", using Python conventions and best practices when possible, and favouring easy to understand names over functional programming jargon.
