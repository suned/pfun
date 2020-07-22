import urllib.parse
from typing import Any, Iterable, Type, TypeVar, Union

from typing_extensions import Protocol

from .dict import Dict
from .effect import (Effect, Resource, Try, add_repr, error, get_environment,
                     success)
from .either import Either, Left, Right
from .functions import curry
from .immutable import Immutable
from .list import List

try:
    import asyncpg
except ImportError:
    raise ImportError(
        'Could not import asyncpg. To use pfun.effect.sql, '
        'install pfun with \n\n\tpip install pfun[sql]'
    )


class EmptyResultSet(Exception):
    pass


SQLError = Union[asyncpg.PostgresError, EmptyResultSet]


class PostgresConnection(Immutable):
    """
    Wrapper for `asyncpg.Connection` to make it useable with
    `Resource`
    """
    connection: asyncpg.Connection

    async def __aenter__(self):
        pass

    async def __aexit__(self, *args, **kwargs):
        await self.connection.close()


Results = List[Dict[str, Any]]
"""
Type-alias for `pfun.list.List[pfun.dict.Dict[str, typing.Any]]`
"""
Results.__module__ = __name__

T = TypeVar('T')


@curry
def as_type(type_: Type[T], results: Results) -> Try[TypeError, List[T]]:
    """
    Convert database results to `type_`

    Example:
        >>> results = pfun.effect.success(
        ...     pfun.List([pfun.Dict(dict(name='bob', age=32))])
        ... )
        >>> class User(pfun.Immutable):
        ...     name: str
        ...     age: int
        >>> results.and_then(as_type(User))(None)
        List((User(name='bob', age=32),))

    Args:
        type_: type to convert database results to
        results: database results to convert

    :return: ``List`` of database results converted to `type_`
    """

    try:
        return success(List(type_(**row) for row in results)  # type: ignore
                       )
    except TypeError as e:
        return error(e)


class MalformedConnectionStr(Exception):
    """
    Error returned when a malformed connection str is passed to `SQL`
    """


class SQL(Immutable, init=False):
    """
    Module providing postgres sql client capability
    """
    connection: Resource[asyncpg.PostgresError, PostgresConnection]

    def __init__(self, connection_str: str):
        """
        Create an SQL module

        Args:
            connection_str: connection string of the format \
            `postgres://<user>:<password>@<host>/<database>`
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

    def get_connection(self
                       ) -> Try[asyncpg.PostgresError, asyncpg.Connection]:
        """
        Get an `Effect` that produces a
        `asyncpg.Connection`. Used to work with `asyncpg` directly.

        Example:
            >>> sql = SQL('postgres://user@host/database')
            >>> sql.get_connection()(None)
            <asyncpg.connection.Connection at ...>

        Return:
            `Effect` that produces `asyncpg.Connection`
        """
        return self.connection.get().map(lambda c: c.connection)

    def execute(self, query: str, *args: Any,
                timeout: float = None) -> Try[asyncpg.PostgresError, str]:
        """
        Get an `Effect` that executes `query`

        Example:
            >>> sql = SQL('postgres://user@host/database')
            >>> sql.execute(
            ...     'INSERT INTO users(name, age) VALUES($1, $2)',
            ...     'bob',
            ...     32
            ... )(None)
            'INSERT 1'

        Args:
            query: query to execute
            args: arguments for query
            timeout: query timeout

        Return:
            `Effect` that executes `query` and produces the database response
        """
        async def _execute(connection: asyncpg.Connection
                           ) -> Try[asyncpg.PostgresError, str]:
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
    ) -> Try[asyncpg.PostgresError, Iterable[str]]:
        """
        Get an `Effect` that executes `query` for each argument \
        in `args`

        Example:
            >>> sql = SQL('postgres://user@host/database')
            >>> sql.execute_many(
            ...     'INSERT INTO users(name, age) VALUES($1, $2)',
            ...     [('bob', 32), ('alice', 20)]
            ... )(None)
            'INSERT 2'

        Args:
            query: query to execute
            args: arguments for query
            timeout: query timeout

        Return:
            `Effect` that executes `query` with all args in `args` and \
            produces a database response for each query
        """
        async def _execute_many(connection: asyncpg.Connection
                                ) -> Try[asyncpg.PostgresError, str]:
            try:
                result = await connection.executemany(
                    query, *args, timeout=timeout
                )
                return success(result)
            except asyncpg.PostgresError as e:
                return error(e)

        return self.get_connection().and_then(_execute_many)

    def fetch(self, query: str, *args: Any,
              timeout: float = None) -> Try[asyncpg.PostgresError, Results]:
        """
        Get an `Effect` that executes `query` and returns the results
        as a `List` of `Dict`

        Example:
            >>> sql = SQL('postgres://user@host/database')
            >>> sql.fetch('select * from users')(None)
            List((Dict({'name': 'bob', 'age': 32}),))

        Args:
            query: query to execute
            args: arguments for query
            timeout: query timeout

        Return:
            `Effect` that retrieves rows returned by `query` as `Results`
        """
        async def _fetch(connection: asyncpg.Connection
                         ) -> Try[asyncpg.PostgresError, Results]:
            try:
                result = await connection.fetch(query, *args, timeout=timeout)
                result = List(Dict(record) for record in result)
                return success(result)
            except asyncpg.PostgresError as e:
                return error(e)

        return self.get_connection().and_then(_fetch)

    def fetch_one(self, query: str, *args: Any, timeout: float = None
                  ) -> Try[SQLError, Dict[str, Any]]:
        """
        Get an `Effect` that executes `query` and returns the first \
        result as a `Dict`

        Example:
            >>> sql = SQL('postgres://user@host/database')
            >>> sql.fetch_one('select * from users')(None)
            Dict({'name': 'bob', 'age': 32})

        Args:
            query: query to execute
            args: arguments for query
            timeout: query timeout

        Return:
            `Effect` that retrieves the first row returned by `query` as \
            `pfun.dict.Dict[str, Any]`
        """
        async def _fetch_row(connection: asyncpg.Connection
                             ) -> Try[asyncpg.PostgresError, Dict[str, Any]]:
            try:
                result = await connection.fetchrow(
                    query, *args, timeout=timeout
                )
                if result is None:
                    return error(EmptyResultSet())
                return success(Dict(result))
            except asyncpg.PostgresError as e:
                return error(e)

        return self.get_connection().and_then(_fetch_row)


class HasSQL(Protocol):
    """
    Module provider for the SQL module
    """
    sql: SQL


@add_repr
def get_connection(
) -> Effect[HasSQL, asyncpg.PostgresError, asyncpg.Connection]:
    """
    Get an `Effect` that produces a
    `asyncpg.Connection`. Used to work with `asyncpg` directly.

    Example:
        >>> class Env:
        ...     sql = SQL('postgres://user@host/database')
        >>> get_connection()(Env())
        <asyncpg.connection.Connection at ...>

    Return:
        `Effect` that produces `asyncpg.Connection`
    Return:
        `Effect` that produces `asyncpg.Connection`
    """
    return get_environment(HasSQL
                           ).and_then(lambda env: env.sql.get_connection())


@add_repr
def execute(query: str, *args: Any, timeout: float = None
            ) -> Effect[HasSQL, asyncpg.PostgresError, str]:
    """
    Get an `Effect` that executes `query`

    Example:
        >>> class Env:
        ...     sql = SQL('postgres://user@host/database')
        >>> execute(
        ...     'INSERT INTO users(name, age) VALUES($1, $2)',
        ...     'bob',
        ...     32
        ... )(Env())
        'INSERT 1'

    Args:
        query: query to execute
        args: arguments for query
        timeout: query timeout
    Return:
        `Effect` that executes `query` and produces the database response
    """
    return get_environment(HasSQL).and_then(
        lambda env: env.sql.execute(query, *args, timeout=timeout)
    )


@add_repr
def execute_many(query: str, args: Iterable[Any], timeout: float = None
                 ) -> Effect[HasSQL, asyncpg.PostgresError, Iterable[str]]:
    """
    Get an `Effect` that executes `query` for each argument \
    in `args`

    Example:
        >>> class Env:
        ...     sql = SQL('postgres://user@host/database')
        >>> execute_many(
        ...     'INSERT INTO users(name, age) VALUES($1, $2)',
        ...     [('bob', 32), ('alice', 20)]
        ... )(Env())
        'INSERT 2'

    Args:
        query: query to execute
        args: arguments for query
        timeout: query timeout
    Return:
        `Effect` that executes `query` with all args in `args` and \
        produces a database response for each query
    """
    return get_environment(HasSQL).and_then(
        lambda env: env.sql.execute_many(query, args, timeout=timeout)
    )


@add_repr
def fetch(query: str, *args: Any, timeout: float = None
          ) -> Effect[HasSQL, asyncpg.PostgresError, Results]:
    """
    Get an `Effect` that executes `query` and returns the results
    as a `List` of `Dict`

    Example:
        >>> class Env:
        ...     sql = SQL('postgres://user@host/database')
        >>> fetch('select * from users')(Env())
        List((Dict({'name': 'bob', 'age': 32}),))
    Args:
        query: query to execute
        args: arguments for query
        timeout: query timeout
    Return:
        `Effect` that retrieves rows returned by `query` as `Results`
    """
    return get_environment(HasSQL).and_then(
        lambda env: env.sql.fetch(query, *args, timeout=timeout)
    )


@add_repr
def fetch_one(query: str, *args: Any, timeout: float = None
              ) -> Effect[HasSQL, SQLError, Dict[str, Any]]:
    """
    Get an `Effect` that executes `query` and returns the first \
    result as a `Dict`

    Example:
        >>> class Env:
        ...     sql = SQL('postgres://user@host/database')
        >>> fetch_one('select * from users')(None)
        Dict({'name': 'bob', 'age': 32})

    Args:
        query: query to execute
        args: arguments for query
        timeout: query timeout

    Return:
        `Effect` that retrieves the first row returned by `query` as \
        `pfun.dict.Dict[str, Any]`
    """
    return get_environment(HasSQL).and_then(
        lambda env: env.sql.fetch_one(query, *args, timeout=timeout)
    )
