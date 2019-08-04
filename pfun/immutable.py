import functools
from typing import TypeVar

T = TypeVar('T')


def _initialized_flag(cls):
    return f'_{cls.__name__}__initialized'


def _decorate_setattr(cls):
    __setattr__ = cls.__setattr__

    @functools.wraps(__setattr__)
    def decorator(self, name, value):
        initialized_flag = _initialized_flag(type(self))
        if getattr(self, initialized_flag, False):
            raise AttributeError(f'{self} is immutable')
        __setattr__(self, name, value)
    return decorator


def _decorate_init(cls):
    __init__ = cls.__init__
    initialized_flag = _initialized_flag(cls)

    @functools.wraps(__init__)
    def decorator(self, *args, **kwargs):
        __init__(self, *args, **kwargs)
        setattr(self, initialized_flag, True)
    return decorator


class Immutable:
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
    def __init_subclass__(cls):
        super().__init_subclass__()
        cls.__setattr__ = _decorate_setattr(cls)
        cls.__init__ = _decorate_init(cls)
        return cls

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
        flags = [_initialized_flag(cls)
                 for cls in type(self).__mro__
                 if issubclass(cls, Immutable) and cls is not Immutable]
        for flag in flags:
            del attrs[flag]
        attrs.update(kwargs)
        return type(self)(**attrs)  # type: ignore
