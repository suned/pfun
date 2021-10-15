from dataclasses import dataclass


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

    def __init_subclass__(cls,
                          init: bool = True,
                          repr: bool = True,
                          eq: bool = True,
                          order: bool = False,
                          unsafe_hash: bool = False) -> None:
        super().__init_subclass__()
        if not hasattr(cls, '__annotations__'):
            cls.__annotations__ = {}
        dataclass(
            frozen=True, init=init, repr=repr, eq=eq, order=order
        )(cls)


__all__ = ['Immutable']
