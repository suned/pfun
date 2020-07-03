from typing import Any, NoReturn

from typing_extensions import Protocol

from ..aio_trampoline import Done
from ..either import Right
from ..immutable import Immutable
from .effect import Effect, get_environment

try:
    import aiohttp
except ImportError:
    raise ImportError(
        'Could not import aiohttp. To use pfun.effect.http, '
        'install pfun with \n\n\tpip install pfun[http]'
    )


class Response(Immutable):
    content: bytes
    status_code: int
    headers: bytes


class HTTP(Immutable):
    async def get_session(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession()

    def get(self, url: str) -> Effect[Any, NoReturn, Response]:
        async def run_e(_):
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    content = await response.read()
                    return Done(
                        Right(
                            Response(
                                content, response.status, response.raw_headers
                            )
                        )
                    )

        return Effect(run_e)


class HasHTTP(Protocol):
    http: HTTP


def get_session() -> Effect[HasHTTP, NoReturn, aiohttp.ClientSession]:
    """
    Get an effect that produces an :class:`aiohttp.ClientSession`

    :example:
    >>> async def use_session(session: aiohttp.ClientSession) -> str:
    ...     async with session:
    ...         async with session.get('http://www.google.com') as response:
    ...             return await response.text()
    >>> class Env:
    ...     http = HTTP()
    >>> get_session().map(use_session).run(Env())
    "<!doctype html> ..."
    """
    return get_environment().map(lambda env: env.http.get_session())


def get(url: str) -> Effect[HasHTTP, NoReturn, Response]:
    return get_environment().and_then(lambda env: env.http.get(url))
