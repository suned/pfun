from dataclasses import dataclass
from typing import TypeVar


T = TypeVar('T')


@dataclass(frozen=True)
class Immutable:
    __immutable__ = True
    """
    Abstract super class that makes subclasses immutable after ``__init__``
    returns.

    >>> class A(Immutable):
    ...     def __init__(self, a)
    ...         self.a = a
    >>> class B(A):
    ...     def __init__(self, a, b):
    ...         super().__init__(a)
    ...         self.b = b
    >>> b = B('a', 'b')
    >>> b.a = 'new value'
    AttributeError: <__main__.B object at 0x10f99a0f0> is immutable

    """
    def __init_subclass__(cls, init=True, repr=True, eq=True, order=False, unsafe_hash=False):
        super().__init_subclass__()
        return dataclass(frozen=True, init=init, repr=repr, eq=eq, order=order)(cls)

    def clone(self: T, **kwargs) -> T:
        """
        Make a copy of an instance, potentially overwriting fields given by
        ``kwargs``

        :example:
        >>> class A(Immutable):
        ...     def __init__(self, a):
        ...         self.a = a
        >>> a = A('a')
        >>> a2 = a.clone(a='new value')
        >>> a2.a
        "new value"

        :param kwargs: fields to overwrite
        :return: New instance of same type with copied and overwritten fields

        """
        attrs = self.__dict__.copy()
        attrs.update(kwargs)
        return type(self)(**attrs)  # type: ignore
