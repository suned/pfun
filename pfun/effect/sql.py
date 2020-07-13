import urllib.parse
from typing import Any, Iterable, Type, TypeVar

from typing_extensions import Protocol

from ..curry import curry
from ..dict import Dict
from ..either import Either, Left, Right
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
    """
    Wrapper for :class:`asyncpg.Connection` to make it useable with
    :class:`Resource`
    """
    connection: asyncpg.Connection

    async def __aenter__(self):
        pass

    async def __aexit__(self, *args, **kwargs):
        await self.connection.close()


Results = List[Dict[str, Any]]

T = TypeVar('T')


@curry
def as_type(type_: Type[T],
            results: Results) -> Effect[Any, TypeError, List[T]]:
    """
    Convert database results to `type_`

    :example:
    >>> results = pfun.effect.success(
    ...     pfun.List([pfun.Dict(dict(name='bob', age=32))])
    ... )
    >>> class User(pfun.Immutable):
    ...     name: str
    ...     age: int
    >>> results.and_then(as_type(User))(None)
    List((User(name='bob', age=32),))

    :param type_: type to convert database results to
    :param results: database results to convert

    :return: :class:``List`` of database results converted to `type_`
    """

    try:
        return success(List(type_(**row) for row in results)  # type: ignore
                       )
    except TypeError as e:
        return error(e)


class MalformedConnectionStr(Exception):
    pass


class SQL(Immutable, init=False):
    """
    Module providing postgres sql client capability
    """
    connection: Resource[asyncpg.PostgresError, PostgresConnection]

    def __init__(self, connection_str: str):
        """
        Create an SQL module

        :param connection_str: connection string of the format \
            'postgres://<user>:<password>@<host>/<database>'
        """
        url = urllib.parse.urlparse(connection_str)
        if url.scheme not in {'postgresql', 'postgres'}:
            raise MalformedConnectionStr(connection_str)

        async def connection_factory(
        ) -> Either[asyncpg.PostgresError, PostgresConnection]:
            try:
                return Right(
                    PostgresConnection(await asyncpg.connect(connection_str))
                )
            except asyncpg.PostgresError as e:
                return Left(e)

        object.__setattr__(self, 'connection', Resource(connection_factory))

    def get_connection(
        self
    ) -> Effect[Any, asyncpg.PostgresError, asyncpg.Connection]:
        """
        Get an :class:`Effect` that produces a
        :class:`asyncpg.Connection`. Used to work with `asyncpg` directly.

        :example:
        >>> sql = SQL('postgres://user@host/database')
        >>> sql.get_connection()(None)
        <asyncpg.connection.Connection at ...>

        :return: :class:`Effect` that produces :class:`asyncpg.Connection`
        """
        return self.connection.get().map(lambda c: c.connection)

    def execute(self, query: str, *args: Any, timeout: float = None
                ) -> Effect[Any, asyncpg.PostgresError, str]:
        """
        Get an :class:`Effect` that executes `query`

        :example:
        >>> sql = SQL('postgres://user@host/database')
        >>> sql.execute(
        ...     'INSERT INTO users(name, age) VALUES($1, $2)',
        ...     'bob',
        ...     32
        ... )(None)
        'INSERT 1'

        :param query: query to execute
        :param args: arguments for query
        :param timetout: query timeout
        """
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
        """
        Get an :class:`Effect` that executes `query` for each argument \
        in `args`

        :example:
        >>> sql = SQL('postgres://user@host/database')
        >>> sql.execute_many(
        ...     'INSERT INTO users(name, age) VALUES($1, $2)',
        ...     [('bob', 32), ('alice', 20)]
        ... )(None)
        'INSERT 2'

        :param query: query to execute
        :param args: arguments for query
        :param timetout: query timeout
        """
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
        """
        Get an :class:`Effect` that executes `query` and returns the results
        as a :class:`List` of :class:`Dict`

        :example:
        >>> sql = SQL('postgres://user@host/database')
        >>> sql.fetch('select * from users')(None)
        List((Dict({'name': 'bob', 'age': 32}),))

        :param query: query to execute
        :param args: arguments for query
        :param timetout: query timeout
        """
        async def _fetch(connection: asyncpg.Connection
                         ) -> Effect[Any, asyncpg.PostgresError, Results]:
            try:
                result = await connection.fetch(query, *args, timeout=timeout)
                result = List(Dict(record) for record in result)
                return success(result)
            except asyncpg.PostgresError as e:
                return error(e)

        return self.get_connection().and_then(_fetch)

    def fetch_one(self, query: str, *args: Any, timeout: float = None
                  ) -> Effect[Any, asyncpg.PostgresError, Dict[str, Any]]:
        """
        Get an :class:`Effect` that executes `query` and returns the first \
        result as a :class:`Dict`

        :example:
        >>> sql = SQL('postgres://user@host/database')
        >>> sql.fetch_one('select * from users')(None)
        Dict({'name': 'bob', 'age': 32})

        :param query: query to execute
        :param args: arguments for query
        :param timetout: query timeout
        """
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


class HasSQL(Protocol):
    """
    Module provider for the SQL module
    """
    sql: SQL


def get_connection(
) -> Effect[HasSQL, asyncpg.PostgresError, asyncpg.Connection]:
    """
    Get an :class:`Effect` that produces a
    :class:`asyncpg.Connection`. Used to work with `asyncpg` directly.

    :example:
    >>> class Env:
    ...     sql = SQL('postgres://user@host/database')
    >>> get_connection()(Env())
    <asyncpg.connection.Connection at ...>

    :return: :class:`Effect` that produces :class:`asyncpg.Connection`
    """
    return get_environment().and_then(lambda env: env.sql.get_connection())


def execute(query: str, *args: Any, timeout: float = None
            ) -> Effect[HasSQL, asyncpg.PostgresError, str]:
    """
    Get an :class:`Effect` that executes `query`

    :example:
    >>> class Env:
    ...     sql = SQL('postgres://user@host/database')
    >>> execute(
    ...     'INSERT INTO users(name, age) VALUES($1, $2)',
    ...     'bob',
    ...     32
    ... )(Env())
    'INSERT 1'

    :param query: query to execute
    :param args: arguments for query
    :param timetout: query timeout
    """
    return get_environment(
    ).and_then(lambda env: env.sql.execute(query, *args, timeout=timeout))


def execute_many(query: str, args: Iterable[Any], timeout: float = None
                 ) -> Effect[HasSQL, asyncpg.PostgresError, Iterable[str]]:
    """
    Get an :class:`Effect` that executes `query` for each argument \
    in `args`

    :example:
    >>> class Env:
    ...     sql = SQL('postgres://user@host/database')
    >>> execute_many(
    ...     'INSERT INTO users(name, age) VALUES($1, $2)',
    ...     [('bob', 32), ('alice', 20)]
    ... )(Env())
    'INSERT 2'

    :param query: query to execute
    :param args: arguments for query
    :param timetout: query timeout
    """
    return get_environment(
    ).and_then(lambda env: env.sql.execute_many(query, args, timeout=timeout))


def fetch(query: str, *args: Any, timeout: float = None
          ) -> Effect[HasSQL, asyncpg.PostgresError, Results]:
    """
    Get an :class:`Effect` that executes `query` and returns the results
    as a :class:`List` of :class:`Dict`

    :example:
    >>> class Env:
    ...     sql = SQL('postgres://user@host/database')
    >>> fetch('select * from users')(Env())
    List((Dict({'name': 'bob', 'age': 32}),))

    :param query: query to execute
    :param args: arguments for query
    :param timetout: query timeout
    """
    return get_environment(
    ).and_then(lambda env: env.sql.fetch(query, *args, timeout=timeout))


def fetch_one(query: str, *args: Any, timeout: float = None
              ) -> Effect[HasSQL, asyncpg.PostgresError, Dict[str, Any]]:
    """
    Get an :class:`Effect` that executes `query` and returns the first \
    result as a :class:`Dict`

    :example:
    >>> class Env:
    ...     sql = SQL('postgres://user@host/database')
    >>> fetch_one('select * from users')(None)
    Dict({'name': 'bob', 'age': 32})

    :param query: query to execute
    :param args: arguments for query
    :param timetout: query timeout
    """
    return get_environment(
    ).and_then(lambda env: env.sql.fetch_one(query, *args, timeout=timeout))
