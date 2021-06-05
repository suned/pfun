from dataclasses import dataclass
from typing import TypeVar

T = TypeVar('T')


class Immutable:
    """
    Super class that makes subclasses immutable using dataclasses

    Example:
        >>> class A(Immutable):
        ...     a: str
        >>> class B(A):
        ...     b: str
        >>> b = B('a', 'b')
        >>> b.a = 'new value'
        AttributeError: <__main__.B object at 0x10f99a0f0> is immutable

    """

    def __init_subclass__(
        cls, init=True, repr=True, eq=True, order=False, unsafe_hash=False
    ):
        super().__init_subclass__()
        if not hasattr(cls, '__annotations__'):
            cls.__annotations__ = {}
        return dataclass(
            frozen=True, init=init, repr=repr, eq=eq, order=order
        )(cls)


__all__ = ['Immutable']
