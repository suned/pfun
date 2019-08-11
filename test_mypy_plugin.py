from pfun import compose


def f(a: str) -> str:
    pass


def g(a: str) -> int:
    pass


reveal_type(compose(f, g))


"""
Considerations:
- Arguments to compose must be unary. 
  For error reporting what should the expected type of "(a: Any, b: Any) -> Any" be?
    - (a: Any) -> (b: Any) -> Any?
    - (a: Any) -> Any?
"""
