from typing import Any, Iterable, NoReturn, Type, TypeVar

from typing_extensions import Protocol

from ..curry import curry
from ..dict import Dict
from ..immutable import Immutable
from ..list import List
from .effect import Effect, Resource, error, get_environment, success

try:
    import asyncpg
except ImportError:
    raise ImportError(
        'Could not import asyncpg. To use pfun.effect.sql, '
        'install pfun with \n\n\tpip install pfun[sql]'
    )


class PostgresConnection(Immutable):
    connection: asyncpg.Connection

    async def __aenter__(self):
        pass

    async def __aexit__(self, *args, **kwargs):
        await self.connection.close()


Results = List[Dict[str, Any]]

T = TypeVar('T')


@curry
def as_type(type_: Type[T], results: Results
            ) -> Effect[Any, TypeError, List[T]]:
    try:
        if isinstance(results, List):
            return success(
                List(type_(**row) for row in results)  # type: ignore
            )
        return success(type_(**results))  # type: ignore
    except TypeError as e:
        return error(e)


class SQL(Immutable, init=False):
    connection: Resource[PostgresConnection]

    def __init__(self, connection_str: str):
        async def connection_factory():
            return PostgresConnection(await asyncpg.connect(connection_str))

        object.__setattr__(self, 'connection', Resource(connection_factory))

    def get_connection(self) -> Effect[Any, NoReturn, asyncpg.Connection]:
        return self.connection.get().map(lambda c: c.connection)

    def execute(self, query: str, *args: Any, timeout: float = None
                ) -> Effect[Any, asyncpg.PostgresError, str]:
        async def _execute(connection: asyncpg.Connection
                           ) -> Effect[Any, asyncpg.PostgresError, str]:
            try:
                result = await connection.execute(
                    query, *args, timeout=timeout
                )
                return success(result)
            except asyncpg.PostgresError as e:
                return error(e)

        return self.get_connection().and_then(_execute)

    def execute_many(
        self, query: str, args: Iterable[Any], timeout: float = None
    ) -> Effect[Any, asyncpg.PostgresError, Iterable[str]]:
        async def _execute_many(connection: asyncpg.Connection
                                ) -> Effect[Any, asyncpg.PostgresError, str]:
            try:
                result = await connection.executemany(
                    query, *args, timeout=timeout
                )
                return success(result)
            except asyncpg.PostgresError as e:
                return error(e)

        return self.get_connection().and_then(_execute_many)

    def fetch(self, query: str, *args: Any, timeout: float = None
              ) -> Effect[Any, asyncpg.PostgresError, Results]:
        async def _fetch(connection: asyncpg.Connection
                         ) -> Effect[Any, asyncpg.PostgresError, Results]:
            try:
                result = await connection.fetch(query, *args, timeout=timeout)
                result = List(Dict(record) for record in result)
                return success(result)
            except asyncpg.PostgresError as e:
                return error(e)

        return self.get_connection().and_then(_fetch)

    def fetch_row(self, query: str, *args: Any, timeout: float = None
                  ) -> Effect[Any, asyncpg.PostgresError, Dict[str, Any]]:
        async def _fetch_row(
            connection: asyncpg.Connection
        ) -> Effect[Any, asyncpg.PostgresError, Dict[str, Any]]:
            try:
                result = await connection.fetch_row(
                    query, *args, timeout=timeout
                )
                return success(Dict(result))
            except asyncpg.PostgresError as e:
                return error(e)

        return self.get_connection().and_then(_fetch_row)

    def fetch_val(self, query: str, *args: Any, timeout: float = None
                  ) -> Effect[Any, asyncpg.PostgresError, Any]:
        async def _fetch_val(
            connection: asyncpg.Connection
        ) -> Effect[Any, asyncpg.PostgresError, Dict[str, Any]]:
            try:
                result = await connection.fatchval(
                    query, *args, timeout=timeout
                )
                return success(result)
            except asyncpg.PostgresError as e:
                return error(e)

        return self.get_connection().and_then(_fetch_val)


class HasSQL(Protocol):
    sql: SQL


def get_connection() -> Effect[HasSQL, NoReturn, asyncpg.Connection]:
    return get_environment().and_then(lambda env: env.sql.get_connection())
