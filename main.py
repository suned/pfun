from __future__ import annotations

from fastapi import FastAPI
from typing_extensions import Protocol

from pfun import Depends, Effect, Immutable, List, get_environment, sql


class Todo(Immutable):
    id: int
    content: str


Todos = List[Todo]


class Model:
    def get_todos(self) -> Effect[sql.HasSQL, Exception, Todos]:
        return sql.fetch('select * from todos').and_then(
            sql.as_type(Todo)
        )


class HasModel(Protocol):
    model: Model


class Env:
    model: Model = Model()
    # this is bad
    sql: sql.SQL = sql.SQL('postgres://postgres:password@localhost/todo')


app = FastAPI()


@app.get("/")
async def get_todos() -> Todos:
    # this is a litle fucked
    todos: Depends[Env, Todos] = get_environment().and_then(
        lambda env: env.model.get_todos()
    )
    # this is annoying
    return await todos.run_async(Env())
