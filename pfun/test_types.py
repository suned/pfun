from .maybe import unwrap, Just, Wrap
from typing import Any


@unwrap
def f() -> Wrap[int, str]:
    a = yield Just(1)
    b = yield Just(2)
    return str(a + b)


reveal_type(f)
