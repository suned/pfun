import operator
from typing import Container, Optional, TypeVar, overload

from . import protocols
from .functions import Unary, curry

A = TypeVar('A')
B = TypeVar('B')


@curry
def lt(a: protocols.SupportsLt[A, B], b: A) -> B:
    """
    Return `a < b`, for _a_ and _b_.

    Example:
        >>> lt(1)(2)
        True

    Args:
        a: left element of lt expression
        b: right element of lt expression

    Return:
        `True` if `a < b`, `False` otherwise
    """
    return a < b


@curry
def le(a: protocols.SupportsLe[A, B], b: A) -> B:
    """
    Return `a <= b`, for _a_ and _b_.

    Example:
        >>> le(1)(2)
        True

    Args:
        a: left element of le expression
        b: right element of le expression

    Return:
        `True` if `a <= b`, `False` otherwise
    """
    return a <= b


@curry
def eq(a: object, b: object) -> bool:
    """
    Return `a == b`, for _a_ and _b_.

    Example:
        >>> eq(2)(2)
        True

    Args:
        a: left element of eq expression
        b: right element of eq expression

    Return:
        `True` if `a == b`, `False` otherwise
    """
    return a == b


@curry
def ne(a: object, b: object) -> bool:
    """
    Return `a != b`, for _a_ and _b_.

    Example:
        >>> ne(2)(2)
        False

    Args:
        a: left element of ne expression
        b: right element of ne expression

    Return:
        `True` if `a != b`, `False` otherwise
    """
    return a != b


@curry
def gt(a: protocols.SupportsGt[A, B], b: A) -> B:
    """
    Return `a > b`, for _a_ and _b_.

    Example:
        >>> gt(1)(2)
        False

    Args:
        a: left element of gt expression
        b: right element of gt expression

    Return:
        `True` if `a > b`, `False` otherwise
    """
    return a > b


def not_(a: object) -> bool:
    """
    Return `not a`, for _a_.

    Example:
        >>> not_(True)
        False

    Args:
        a: argument of `not` expression

    Return:
        `False` if `a`, `True` otherwise
    """
    return not a


def truth(a: object) -> bool:
    """
    Return `bool(a)`, for _a_.

    Example:
        >>> truth(True)
        True

    Args:
        a: argument of `bool` expression

    Return:
        `True` if `a`, `False` otherwise
    """
    return bool(a)


@curry
def is_(a: object, b: object) -> bool:
    """
    Return `a is b`, for _a_ and _b_.

    Example:
        >>> is_(object())(object())
        False

    Args:
        a: left element of is expression
        b: right element of is expression

    Return:
        `True` if `a is b`, `False` otherwise
    """
    return a is b


@curry
def is_not(a: object, b: object) -> bool:
    """
    Return `a is not b`, for _a_ and _b_.

    Example:
        >>> is_not(object())(object())
        True

    Args:
        a: left element of is not expression
        b: right element of is not expression

    Return:
        `False` if `a is b`, `True` otherwise
    """
    return a is not b


@curry
def add(a: protocols.SupportsAdd[A, B], b: A) -> B:
    """
    Return `a + b`, for _a_ and _b_.

    Example:
        >>> add(2)(2)
        4

    Args:
        a: left element of add expression
        b: right element of add expression

    Return:
        b added to a
    """
    return a + b


def abs(a: protocols.SupportsAbs[A]) -> A:
    """
    Return builtin `abs(a)`, for _a_.

    Example:
        >>> abs(-2)
        2

    Args:
        a: element of abs expression

    Return:
        b added to a
    """
    return operator.abs(a)


@overload
def and_(a: protocols.SupportsBool) -> Unary[protocols.SupportsBool, bool]:
    ...


@overload
def and_(a: protocols.SupportsAnd[A, B]) -> Unary[A, B]:
    ...


def and_(a) -> Unary:
    """
    Return `a and b`, for _a_ and _b_.

    Example:
        >>> and_(True)(False)
        False

    Args:
        a: left element of and_ expression
        b: right element of and_ expression

    Return:
        True if both `a` and `b`, False otherwise
    """
    return curry(operator.and_)(a)


@curry
def floordiv(a: protocols.SupportsFloorDiv[A, B], b: A) -> B:
    """
    Return `a // b`, for _a_ and _b_.

    Example:
        >>> floordiv(2)(3)
        0

    Args:
        a: left element of // expression
        b: right element of // expression

    Return:
        b added to a
    """
    return a // b


def index(a: protocols.SupportsIndex) -> int:
    """
    Return _a_ converted to an integer. Equivalent to a.__index__().

    Example:
        >>> class Index:
        ...     def __index__(self) -> int:
        ...         return 0
        >>> [1][Index()]
        1

    Args:
        a:
    """
    return operator.index(a)


def invert(a: protocols.SupportsInvert[A]) -> A:
    """
    Return `~a` for _a_.

    Example:
        >>> invert(2)
        -3

    Args:
        a: value to invert

    Return:
        `~a`
    """
    return ~a


@curry
def lshift(a: protocols.SupportsLShift[A, B], b: A) -> B:
    """
    Return `a << b`, for _a_ and _b_.

    Example:
        >>> lshift(2)(3)
        0

    Args:
        a: left element of << expression
        b: right element of << expression

    Return:
        `a` lshifted by `b`
    """
    return a << b


@curry
def mod(a: protocols.SupportsMod[A, B], b: A) -> B:
    """
    Return `a % b`, for _a_ and _b_.

    Example:
        >>> mod(2)(3)
        2

    Args:
        a: left element of % expression
        b: right element of % expression

    Return:
        a modulo b
    """
    return a % b


@curry
def mul(a: protocols.SupportsMul[A, B], b: A) -> B:
    """
    Return `a * b`, for _a_ and _b_.

    Example:
        >>> mul(2)(3)
        6

    Args:
        a: left element of * expression
        b: right element of * expression

    Return:
        a multiplied by b
    """
    return a * b


@curry
def matmul(a: protocols.SupportsMatMul[A, B], b: A) -> B:
    """
    Return `a @ b`, for _a_ and _b_.

    Example:
        >>> import numpy as np
        >>> m = np.arange(3)
        >>> matmul(m)(m)
        5

    Args:
        a: left element of @ expression
        b: right element of @ expression

    Return:
        `a @ b`
    """
    return a @ b


def neg(a: protocols.SupportsNeg[A]) -> A:
    """
    Return `-a`.

    Example:
        >>> neg(5)
        -5

    Args:
        a: element of negation expression

    Return:
        `-a`
    """
    return -a


@overload
def or_(a: protocols.SupportsBool) -> Unary[protocols.SupportsBool, bool]:
    ...


@overload
def or_(a: protocols.SupportsOr[A, B]) -> Unary[A, B]:
    ...


def or_(a) -> Unary:
    """
    Return `a or b`, for _a_ and _b_.

    Example:
        >>> or_(True)(False)
        True

    Args:
        a: left element of or expression
        b: right element of or expression

    Return:
        True if either `a` or `b`, False otherwise
    """
    return curry(operator.or_)(a)


def pos(a: protocols.SupportsPos[A]) -> A:
    """
    Return `+a`.

    Example:
        >>> pos(-5)
        -5

    Args:
        a: element of pos expression

    Return:
        `+a`
    """
    return +a


@curry
def pow(a: protocols.SupportsPow[A, B], b: A) -> B:
    """
    Return `a ** b`, for _a_ and _b_.

    Example:
        >>> pow(2)(2)
        4

    Args:
        a: left element of ** expression
        b: right element of ** expression

    Return:
        `a ** b`
    """
    return a**b


@curry
def rshift(a: protocols.SupportsRShift[A, B], b: A) -> B:
    """
    Return `a >> b`, for _a_ and _b_.

    Example:
        >>> rshift(2)(3)
        0

    Args:
        a: left element of >> expression
        b: right element of >> expression

    Return:
        `a` rshifted by `b`
    """
    return a >> b


@curry
def sub(a: protocols.SupportsSub[A, B], b: A) -> B:
    """
    Return `a - b`, for _a_ and _b_.

    Example:
        >>> sub(2)(2)
        0

    Args:
        a: left element of - expression
        b: right element of - expression

    Return:
        `a - b`
    """
    return a - b


@curry
def truediv(a: protocols.SupportsTrueDiv[A, B], b: A) -> B:
    """
    Return `a / b`, for _a_ and _b_.

    Example:
        >>> truediv(2)(2)
        1.0

    Args:
        a: left element of / expression
        b: right element of / expression

    Return:
        `a / b`
    """
    return a / b


@curry
def xor(a: protocols.SupportsXor[A, B], b: A) -> B:
    """
    Return `a ^ b`, for _a_ and _b_.

    Example:
        >>> xor(2)(2)
        0

    Args:
        a: left element of ^ expression
        b: right element of ^ expression

    Return:
        `a ^ b`
    """
    return a ^ b


@curry
def contains(elem: A, container: Container[A]) -> bool:
    """
    Return `elem in container`, for _elem_ and _container_. \
    Note that the order of arguments are flipped comparet to the builtins \
    `operator` module

    Example:
        >>> contains(2)([1, 2, 3])
        True

    Args:
        elem: left element of `in` expression
        container: right element of `in` expression

    Return:
        `elem in container`
    """
    return operator.contains(container, elem)


@curry
def count_of(elem: A, container: Container[A]) -> int:
    """
    Return count of how many times `elem` appears in `container`. \
    Note that the order of arguments are flipped comparet to the builtins \
    `operator` module

    Example:
        >>> count_of(2)([1, 2, 3])
        1

    Args:
        elem: left element of `in` expression
        container: right element of `in` expression

    Return:
        `elem in container`
    """
    return operator.countOf(container, elem)


@curry
def get_item(index: A,
             container: protocols.SupportsGetItem[A, B]) -> Optional[B]:
    """
    Return element at `index` in `container`. Note that the order \
    of arguments are flipped comparet to the builtins `operator` module

    Example:
        >>> get_item(1)([1, 2, 3])
        2

    Args:
        index: value to use as index
        container: container to index with `index`

    Return:
        `container[index]`
    """
    try:
        return container[index]
    except (KeyError, IndexError):
        return None


@curry
def length_hint(a: protocols.SupportsLengthHint, default: int = 0) -> int:
    """
    Return an estimated length for the object o. \
    First try to return its actual length, then an estimate \
    using `a.__length_hint__()`, and finally return the default value.

    Example:
        >>> length_hint([])
        0

    Args:
        a: value to compute length hint from

    Return:
        Length hint as an int
    """
    return operator.length_hint(a)
