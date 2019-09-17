from pfun.free import (
    Functor, Free, More, Done, FreeInterpreter, FreeInterpreterElement
)
from pfun import Immutable, Dict, compose
from pfun.state import State, get as get_, put as put_

from typing import TypeVar, Callable

A = TypeVar('A')
B = TypeVar('B')


class KVStoreF(Functor, Immutable):
    pass


KVStore = Dict[str, str]
KVStoreInterpreter = FreeInterpreter[KVStore, KVStore]
KVStoreInterpreterState = State[A, KVStore]
KVStoreElement = FreeInterpreterElement[KVStore, KVStore]
KVStoreFree = Free[KVStoreF, A, KVStore, KVStore]
get_state: Callable[[], KVStoreInterpreterState[KVStore]] = get_
set_state: Callable[[KVStore], KVStoreInterpreterState[None]] = put_


class Put(KVStoreF, KVStoreElement):
    k: str
    v: str
    a: KVStoreFree

    def map(self, f: Callable[[KVStoreFree], KVStoreFree]) -> KVStoreF:
        return Put(self.k, self.v, f(self.a))

    def accept(
        self, interpreter: KVStoreInterpreter
    ) -> KVStoreInterpreterState:
        return get_state().and_then(
            lambda s: set_state(s.set(self.k, self.v))
        ).and_then(lambda _: interpreter.interpret(self.a))


class Get(KVStoreF, KVStoreElement):
    key: str
    h: Callable[[str], KVStoreFree]

    def map(self, f: Callable[[KVStoreFree], KVStoreFree]) -> KVStoreF:
        g = compose(f, self.h)  # type: ignore
        return Get(self.key, g)

    def accept(
        self, interpreter: KVStoreInterpreter
    ) -> KVStoreInterpreterState:
        return get_state().and_then(
            lambda s: self.h(s[self.key])  # type: ignore
        ).and_then(
            interpreter.interpret
        )  # yapf: disable


class Delete(KVStoreF, KVStoreElement):
    key: str
    a: KVStoreFree

    def map(self, f: Callable[[KVStoreFree], KVStoreFree]) -> KVStoreF:
        return Delete(self.key, f(self.a))

    def accept(
        self, interpreter: KVStoreInterpreter
    ) -> KVStoreInterpreterState:
        return get_state().and_then(
            lambda s: set_state(s.without(self.key))
        ).and_then(lambda _: interpreter.interpret(self.a))


def put(k: str, v: str) -> KVStoreFree[None]:
    return More(Put(k, v, Done(None)))


def get(k: str) -> KVStoreFree[str]:
    return More(Get(k, lambda v: Done(v)))


def delete(k: str) -> KVStoreFree[None]:
    return More(Delete(k, Done(None)))


def modify(k: str, f: Callable[[str], str]) -> KVStoreFree[None]:
    return get(k).and_then(lambda v: put(k, f(v)))


def run(free: KVStoreFree, table: Dict[str, str]) -> Dict[str, str]:
    _, new_table = KVStoreInterpreter().interpret(free).run(table)
    return new_table
