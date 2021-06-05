from __future__ import annotations

import copy
from typing import Any, Generic, TypeVar

from .dict import Dict
from .immutable import Immutable
from .list import List

A = TypeVar('A')
B = TypeVar('B', covariant=True)


class Transform(Immutable, Generic[A]):
    lens: Lens
    value: Any
    transforms: List[Transform] = List()

    def __repr__(self) -> str:
        sep = ' & '
        updates_repr = (
            sep +
            sep.join([repr(u)
                      for u in self.transforms]) if self.transforms else ''
        )
        return f'{repr(self.lens)} << {repr(self.value)}' + updates_repr

    def __call__(self, a: A) -> A:
        *rest, head = self.lens
        attr_stack = [a]
        for path_element in rest:
            *attrs, last_attr = attr_stack
            next_attr = path_element.get(last_attr)
            attr_stack = attrs + [last_attr, next_attr]
        *attrs, last_attr = attr_stack
        transformed_last_attr = head.set(last_attr, self.value)
        for attr, path_element in zip(reversed(attrs), reversed(rest)):
            transformed_last_attr = path_element.set(
                attr, transformed_last_attr
            )
        for transform in self.transforms:
            transformed_last_attr = transform(transformed_last_attr)
        return transformed_last_attr

    def __and__(self, transform: Transform) -> Transform:
        return Transform(self.lens, self.value, self.transforms + [transform])


class PathElement(Immutable):
    def get(self, x):
        raise NotImplementedError()

    def set(self, x, value):
        raise NotImplementedError()


def _is_named_tuple(x: object) -> bool:
    return (
        isinstance(x, tuple) and hasattr(x, '_fields')
        and hasattr(x, '_asdict') and hasattr(x, '_replace')
    )


class Attr(PathElement):
    attr: str

    def __repr__(self):
        return f'.{self.attr}'

    def get(self, x):
        return getattr(x, self.attr)

    def set(self, x, value):
        if _is_named_tuple(x):
            return x._replace(**{self.attr: value})
        x = copy.copy(x)
        object.__setattr__(x, self.attr, value)
        return x


class Index(PathElement):
    index: Any

    def __repr__(self):
        return f'[{repr(self.index)}]'

    def get(self, x):
        return x[self.index]

    def set(self, x, value):
        if isinstance(x, List):
            x[self.index]
            before = x[:self.index]
            after = x[self.index + 1:]
            return before + List([value]) + after
        elif isinstance(x, tuple):
            x[self.index]
            before = x[:self.index]
            after = x[self.index + 1:]
            return before + (value, ) + after
        elif isinstance(x, Dict):
            return x.set(self.index, value)
        x = copy.copy(x)
        x[self.index] = value
        return x


class RootLens(Immutable):
    __path: List[PathElement] = List()

    def __iter__(self):
        return iter(self.__path)

    def __repr__(self) -> str:
        result = 'lens'
        for path_element in self:
            result += repr(path_element)
        return result

    def __getattr__(self, name: str) -> Lens:
        return Lens(self.__path + [Attr(name)])

    def __getitem__(self, index: Any) -> Lens:
        return Lens(self.__path + [Index(index)])


class Lens(RootLens):
    def __repr__(self):
        return super().__repr__()

    def __lshift__(self, value: Any) -> Transform:
        return Transform(self, value)
