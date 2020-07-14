from __future__ import annotations

from typing import Any, NoReturn, Tuple, TypeVar

from fastapi import FastAPI
from typing_extensions import Protocol

from pfun import Immutable
from pfun.effect import Effect, get_environment, sql

app = FastAPI()


class Model:
    def get_todos(self) -> Effect[sql.HasSQL, Exception, Todos]:
        return sql.fetch('select * from todos').and_then(
            sql.as_type(Todo)
        ).map(tuple)


class HasModel(Protocol):
    model: Model


R = TypeVar('R')
E = TypeVar('E')
A = TypeVar('A')

Depends = Effect[R, NoReturn, A]
IO = Effect[Any, NoReturn, A]
TryIO = Effect[Any, E, A]


class Todo(Immutable):
    id: int
    content: str


Todos = Tuple[Todo, ...]


class View:
    async def get_todos(self) -> Todos:
        todos: Depends[HasModel, Todos] = get_environment().and_then(
            lambda env: env.model.get_todos()
        )
        return await todos.run_async(Env())


class Env:
    model = Model()
    sql = sql.SQL('postgres://postgres:password@localhost/todo')


view = View()

app.get("/")(view.get_todos)
