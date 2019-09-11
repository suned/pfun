from pfun.free import (Functor, Free, More, Done, FreeInterpreter,
                       FreeInterpreterElement)
from pfun import Immutable, Dict, compose

from typing import TypeVar, Callable

A = TypeVar('A')
B = TypeVar('B')


class KVStore(Functor, Immutable):
    pass


KVStoreInterpreter = FreeInterpreter[Dict[str, str], Dict[str, str]]
KVStoreElement = FreeInterpreterElement[Dict[str, str], Dict[str, str]]
KVStoreFree = Free[KVStore, A, Dict[str, str], Dict[str, str]]


class Put(KVStore, KVStoreElement):
    k: str
    v: str
    a: KVStoreFree

    def map(self, f: Callable[[KVStoreFree], KVStoreFree]) -> KVStore:
        return Put(self.k, self.v, f(self.a))

    def accept(self, interpreter: KVStoreInterpreter,
               table: Dict[str, str]) -> Dict[str, str]:
        table = table.set(self.k, self.v)
        return interpreter.interpret(self.a, table)


class Get(KVStore, KVStoreElement):
    key: str
    h: Callable[[str], KVStoreFree]

    def map(self, f: Callable[[KVStoreFree], KVStoreFree]) -> KVStore:
        g = compose(f, self.h)  # type: ignore
        return Get(self.key, g)

    def accept(self, interpreter: KVStoreInterpreter,
               table: Dict[str, str]) -> Dict[str, str]:
        v = table[self.key]
        element = self.h(v)  # type: ignore
        return interpreter.interpret(element, table)


class Delete(KVStore, KVStoreElement):
    key: str
    a: KVStoreFree

    def map(self, f: Callable[[KVStoreFree], KVStoreFree]) -> KVStore:
        return Delete(self.key, f(self.a))

    def accept(self, interpreter: KVStoreInterpreter,
               table: Dict[str, str]) -> Dict[str, str]:
        table = table.without(self.key)
        return interpreter.interpret(self.a, table)


def put(k: str, v: str) -> KVStoreFree[None]:
    return More(Put(k, v, Done(None)))


def get(k: str) -> KVStoreFree[str]:
    return More(Get(k, lambda v: Done(v)))


def delete(k: str) -> KVStoreFree[None]:
    return More(Delete(k, Done(None)))


def modify(k: str, f: Callable[[str], str]) -> KVStoreFree[None]:
    return get(k).and_then(lambda v: put(k, f(v)))


def run(free: KVStoreFree, table: Dict[str, str]) -> Dict[str, str]:
    return KVStoreInterpreter().interpret(free, table)
