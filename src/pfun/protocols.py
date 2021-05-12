from typing import TypeVar

from typing_extensions import Protocol

A = TypeVar('A', contravariant=True)
B = TypeVar('B', covariant=True)


class SupportsCall(Protocol[A, B]):
    def __call__(self, a: A) -> B:
        pass


class SupportsLt(Protocol[A, B]):
    def __lt__(self, other: A) -> B:
        pass


class SupportsGt(Protocol[A, B]):
    def __gt__(self, other: A) -> B:
        pass


class SupportsLe(Protocol[A, B]):
    def __le__(self, other: A) -> B:
        pass


class SupportsEq(Protocol):
    def __eq__(self, other: object) -> bool:
        pass


class SupportsNe(Protocol):
    def __ne__(self, other: object) -> bool:
        pass


class SupportsAdd(Protocol[A, B]):
    def __add__(self, other: A) -> B:
        pass


class SupportsAnd(Protocol[A, B]):
    def __and__(self, other: A) -> B:
        pass


class SupportsOr(Protocol[A, B]):
    def __or__(self, other: A) -> B:
        pass


class SupportsBool(Protocol):
    def __bool__(self) -> bool:
        pass


class SupportsDelItem(Protocol[A]):
    def __delitem__(self, item: A) -> None:
        pass


class SupportsAbs(Protocol[B]):
    def __abs__(self) -> B:
        pass


class SupportsFloorDiv(Protocol[A, B]):
    def __floordiv__(self, b: A) -> B:
        pass


class SupportsIndex(Protocol):
    def __index__(self) -> int:
        pass


class SupportsInvert(Protocol[B]):
    def __invert__(self) -> B:
        pass


class SupportsLShift(Protocol[A, B]):
    def __lshift__(self, b: A) -> B:
        pass


class SupportsRShift(Protocol[A, B]):
    def __rshift__(self, b: A) -> B:
        pass


class SupportsMod(Protocol[A, B]):
    def __mod__(self, b: A) -> B:
        pass


class SupportsMul(Protocol[A, B]):
    def __mul__(self, b: A) -> B:
        pass


class SupportsMatMul(Protocol[A, B]):
    def __matmul__(self, b: A) -> B:
        pass


class SupportsNeg(Protocol[B]):
    def __neg__(self) -> B:
        pass


class SupportsPos(Protocol[B]):
    def __pos__(self) -> B:
        pass


class SupportsPow(Protocol[A, B]):
    def __pow__(self, b: A) -> B:
        pass


class SupportsSub(Protocol[A, B]):
    def __sub__(self, b: A) -> B:
        pass


class SupportsTrueDiv(Protocol[A, B]):
    def __truediv__(self, b: A) -> B:
        pass


class SupportsXor(Protocol[A, B]):
    def __xor__(self, b: A) -> B:
        pass


class SupportsGetItem(Protocol[A, B]):
    def __getitem__(self, b: A) -> B:
        pass


class SupportsLengthHint(Protocol):
    def __length_hint__(self) -> int:
        pass
