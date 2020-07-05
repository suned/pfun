from __future__ import annotations

import http
import json
import ssl
from typing import Any, Callable, Iterable, Mapping, NoReturn, Union

from typing_extensions import Protocol

from ..dict import Dict
from ..immutable import Immutable
from ..maybe import Maybe, from_optional
from .effect import Effect, Module, error, get_environment, success
from .ref import LazyRef

try:
    import aiohttp
    from aiohttp.client_exceptions import ClientError
except ImportError:
    raise ImportError(
        'Could not import aiohttp. To use pfun.effect.http, '
        'install pfun with \n\n\tpip install pfun[http]'
    )


class Response(Immutable):
    content: bytes
    status: int
    reason: Maybe[str]
    cookies: http.cookies.BaseCookie
    headers: Dict[str, str]
    links: Dict[str, str]
    encoding: Maybe[str]


JSonPrim = Union[int, str, float, Dict[str, Any]]
JSon = Union[Iterable[JSonPrim], JSonPrim]


class HTTP(Immutable, Module, init=False):
    session: LazyRef[aiohttp.ClientSession]
    kwargs: dict

    def __init__(
        self,
        connector: aiohttp.connector.BaseConnector = None,
        cookies: Mapping = None,
        headers: Mapping = None,
        skip_auto_headers: Iterable[str] = None,
        auth: aiohttp.BasicAuth = None,
        json_serialize: Callable[[Union[str, bytes]], Any] = json.dumps,
        version: aiohttp.http_writer.HttpVersion = aiohttp.HttpVersion11,
        cookie_jar: aiohttp.client.AbstractCookieJar = None,
        read_timeout: float = None,
        conn_timeout: float = None,
        timeout: aiohttp.ClientTimeout = aiohttp.client.sentinel,
        raise_for_status: bool = False,
        connector_owner: bool = True,
        auto_decompress: bool = True,
        requote_redirect_url: bool = False,
        trust_env: bool = False,
        trace_configs: Iterable[aiohttp.TraceConfig] = None
    ):
        kwargs = {
            'connector': connector,
            'cookies': cookies,
            'headers': headers,
            'skip_auto_headers': skip_auto_headers,
            'auth': auth,
            'json_serialize': json_serialize,
            'version': version,
            'cookie_jar': cookie_jar,
            'read_timeout': read_timeout,
            'conn_timeout': conn_timeout,
            'timeout': timeout,
            'raise_for_status': raise_for_status,
            'connector_owner': connector_owner,
            'auto_decompress': auto_decompress,
            'requote_redirect_url': requote_redirect_url,
            'trust_env': trust_env,
            'trace_configs': trace_configs
        }
        object.__setattr__(self, 'kwargs', kwargs)
        object.__setattr__(
            self,
            'session',
            LazyRef(lambda: aiohttp.ClientSession(**self.kwargs))
        )

    def initialize(self) -> Effect[Any, NoReturn, None]:
        return self.session.modify(
            lambda _: aiohttp.ClientSession(**self.kwargs)
        )

    def finalize(self) -> Effect[Any, NoReturn, None]:
        async def close(session):
            await session.close()

        return self.session.get().map(close)

    def make_request(
        self,
        method: str,
        url: str,
        params: Mapping[str, Any] = None,
        data: Union[aiohttp.FormData, bytes, dict] = None,
        json: JSon = None,
        cookies: Mapping = None,
        headers: Mapping = None,
        skip_auto_headers: Iterable[str] = None,
        auth: aiohttp.BasicAuth = None,
        allow_redirects: bool = True,
        max_redirects: int = 10,
        compress: bool = None,
        chunked: int = None,
        expect100: bool = False,
        raise_for_status: bool = None,
        read_until_eof: bool = True,
        proxy: str = None,
        proxy_auth: aiohttp.BasicAuth = None,
        timeout=aiohttp.client.sentinel,
        ssl: Union[bool, aiohttp.Fingerprint, ssl.SSLContext] = None,
        verify_ssl: bool = None,
        fingerprint: bytes = None,
        ssl_context: ssl.SSLContext = None,
        proxy_headers: Mapping = None
    ) -> Effect[Any, ClientError, Response]:
        async def _make_request(session: aiohttp.ClientSession
                                ) -> Effect[Any, ClientError, Response]:
            try:
                async with session.request(
                    method,
                    url,
                    params=params,
                    data=data,
                    json=json,
                    cookies=cookies,
                    headers=headers,
                    skip_auto_headers=skip_auto_headers,
                    auth=auth,
                    allow_redirects=allow_redirects,
                    max_redirects=max_redirects,
                    compress=compress,
                    chunked=chunked,
                    expect100=expect100,
                    raise_for_status=raise_for_status,
                    read_until_eof=read_until_eof,
                    proxy=proxy,
                    proxy_auth=proxy_auth,
                    timeout=timeout,
                    ssl=ssl,
                    verify_ssl=verify_ssl,
                    fingerprint=fingerprint,
                    ssl_context=ssl_context,
                    proxy_headers=proxy_headers
                ) as response:
                    content = await response.read()
                    return success(
                        Response(
                            content,
                            response.status,
                            from_optional(response.reason),
                            response.cookies,
                            Dict(response.headers),
                            Dict(response.links),
                            from_optional(response.charset)
                        )
                    )
            except ClientError as e:
                return error(e)

        return self.session.get().and_then(_make_request)


class HasHTTP(Protocol):
    http: HTTP


def get_session() -> Effect[HasHTTP, NoReturn, aiohttp.ClientSession]:
    """
    Get an effect that produces an :class:`aiohttp.ClientSession`.
    Use this if you need features of `aiohttp` that are not supported
    by the high-level api.

    :example:
    >>> async def use_session(session: aiohttp.ClientSession) -> str:
    ...     async with session.get('http://www.google.com') as response:
    ...         return await response.text()
    >>> class Env:
    ...     http = HTTP()
    >>> get_session().map(use_session).run(Env())
    "<!doctype html> ..."
    """
    return get_environment().and_then(lambda env: env.http.session.get())


def get(
    url: str,
    params: Mapping[str, Any] = None,
    data: Union[aiohttp.FormData, bytes, dict] = None,
    json: JSon = None,
    cookies: Mapping = None,
    headers: Mapping = None,
    skip_auto_headers: Iterable[str] = None,
    auth: aiohttp.BasicAuth = None,
    allow_redirects: bool = True,
    max_redirects: int = 10,
    compress: bool = None,
    chunked: int = None,
    expect100: bool = False,
    raise_for_status: bool = None,
    read_until_eof: bool = True,
    proxy: str = None,
    proxy_auth: aiohttp.BasicAuth = None,
    timeout=aiohttp.client.sentinel,
    ssl: Union[bool, aiohttp.Fingerprint, ssl.SSLContext] = None,
    verify_ssl: bool = None,
    fingerprint: bytes = None,
    ssl_context: ssl.SSLContext = None,
    proxy_headers: Mapping = None
) -> Effect[HasHTTP, ClientError, Response]:
    """

    """
    return get_environment().and_then(
        lambda env: env.http.make_request(
            'get',
            url,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            headers=headers,
            skip_auto_headers=skip_auto_headers,
            auth=auth,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            compress=compress,
            chunked=chunked,
            expect100=expect100,
            raise_for_status=raise_for_status,
            read_until_eof=read_until_eof,
            proxy=proxy,
            proxy_auth=proxy_auth,
            timeout=timeout,
            ssl=ssl,
            verify_ssl=verify_ssl,
            fingerprint=fingerprint,
            ssl_context=ssl_context,
            proxy_headers=proxy_headers
        )
    )


def put(
    url: str,
    params: Mapping[str, Any] = None,
    data: Union[aiohttp.FormData, bytes, dict] = None,
    json: JSon = None,
    cookies: Mapping = None,
    headers: Mapping = None,
    skip_auto_headers: Iterable[str] = None,
    auth: aiohttp.BasicAuth = None,
    allow_redirects: bool = True,
    max_redirects: int = 10,
    compress: bool = None,
    chunked: int = None,
    expect100: bool = False,
    raise_for_status: bool = None,
    read_until_eof: bool = True,
    proxy: str = None,
    proxy_auth: aiohttp.BasicAuth = None,
    timeout=aiohttp.client.sentinel,
    ssl: Union[bool, aiohttp.Fingerprint, ssl.SSLContext] = None,
    verify_ssl: bool = None,
    fingerprint: bytes = None,
    ssl_context: ssl.SSLContext = None,
    proxy_headers: Mapping = None
) -> Effect[HasHTTP, ClientError, Response]:
    """

    """
    return get_environment().and_then(
        lambda env: env.http.make_request(
            'put',
            url,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            headers=headers,
            skip_auto_headers=skip_auto_headers,
            auth=auth,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            compress=compress,
            chunked=chunked,
            expect100=expect100,
            raise_for_status=raise_for_status,
            read_until_eof=read_until_eof,
            proxy=proxy,
            proxy_auth=proxy_auth,
            timeout=timeout,
            ssl=ssl,
            verify_ssl=verify_ssl,
            fingerprint=fingerprint,
            ssl_context=ssl_context,
            proxy_headers=proxy_headers
        )
    )


def post(
    url: str,
    params: Mapping[str, Any] = None,
    data: Union[aiohttp.FormData, bytes, dict] = None,
    json: JSon = None,
    cookies: Mapping = None,
    headers: Mapping = None,
    skip_auto_headers: Iterable[str] = None,
    auth: aiohttp.BasicAuth = None,
    allow_redirects: bool = True,
    max_redirects: int = 10,
    compress: bool = None,
    chunked: int = None,
    expect100: bool = False,
    raise_for_status: bool = None,
    read_until_eof: bool = True,
    proxy: str = None,
    proxy_auth: aiohttp.BasicAuth = None,
    timeout=aiohttp.client.sentinel,
    ssl: Union[bool, aiohttp.Fingerprint, ssl.SSLContext] = None,
    verify_ssl: bool = None,
    fingerprint: bytes = None,
    ssl_context: ssl.SSLContext = None,
    proxy_headers: Mapping = None
) -> Effect[HasHTTP, ClientError, Response]:
    """

    """
    return get_environment().and_then(
        lambda env: env.http.make_request(
            'post',
            url,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            headers=headers,
            skip_auto_headers=skip_auto_headers,
            auth=auth,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            compress=compress,
            chunked=chunked,
            expect100=expect100,
            raise_for_status=raise_for_status,
            read_until_eof=read_until_eof,
            proxy=proxy,
            proxy_auth=proxy_auth,
            timeout=timeout,
            ssl=ssl,
            verify_ssl=verify_ssl,
            fingerprint=fingerprint,
            ssl_context=ssl_context,
            proxy_headers=proxy_headers
        )
    )


def delete(
    url: str,
    params: Mapping[str, Any] = None,
    data: Union[aiohttp.FormData, bytes, dict] = None,
    json: JSon = None,
    cookies: Mapping = None,
    headers: Mapping = None,
    skip_auto_headers: Iterable[str] = None,
    auth: aiohttp.BasicAuth = None,
    allow_redirects: bool = True,
    max_redirects: int = 10,
    compress: bool = None,
    chunked: int = None,
    expect100: bool = False,
    raise_for_status: bool = None,
    read_until_eof: bool = True,
    proxy: str = None,
    proxy_auth: aiohttp.BasicAuth = None,
    timeout=aiohttp.client.sentinel,
    ssl: Union[bool, aiohttp.Fingerprint, ssl.SSLContext] = None,
    verify_ssl: bool = None,
    fingerprint: bytes = None,
    ssl_context: ssl.SSLContext = None,
    proxy_headers: Mapping = None
) -> Effect[HasHTTP, ClientError, Response]:
    """

    """
    return get_environment().and_then(
        lambda env: env.http.make_request(
            'delete',
            url,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            headers=headers,
            skip_auto_headers=skip_auto_headers,
            auth=auth,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            compress=compress,
            chunked=chunked,
            expect100=expect100,
            raise_for_status=raise_for_status,
            read_until_eof=read_until_eof,
            proxy=proxy,
            proxy_auth=proxy_auth,
            timeout=timeout,
            ssl=ssl,
            verify_ssl=verify_ssl,
            fingerprint=fingerprint,
            ssl_context=ssl_context,
            proxy_headers=proxy_headers
        )
    )


def head(
    url: str,
    params: Mapping[str, Any] = None,
    data: Union[aiohttp.FormData, bytes, dict] = None,
    json: JSon = None,
    cookies: Mapping = None,
    headers: Mapping = None,
    skip_auto_headers: Iterable[str] = None,
    auth: aiohttp.BasicAuth = None,
    allow_redirects: bool = True,
    max_redirects: int = 10,
    compress: bool = None,
    chunked: int = None,
    expect100: bool = False,
    raise_for_status: bool = None,
    read_until_eof: bool = True,
    proxy: str = None,
    proxy_auth: aiohttp.BasicAuth = None,
    timeout=aiohttp.client.sentinel,
    ssl: Union[bool, aiohttp.Fingerprint, ssl.SSLContext] = None,
    verify_ssl: bool = None,
    fingerprint: bytes = None,
    ssl_context: ssl.SSLContext = None,
    proxy_headers: Mapping = None
) -> Effect[HasHTTP, ClientError, Response]:
    """

    """
    return get_environment().and_then(
        lambda env: env.http.make_request(
            'head',
            url,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            headers=headers,
            skip_auto_headers=skip_auto_headers,
            auth=auth,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            compress=compress,
            chunked=chunked,
            expect100=expect100,
            raise_for_status=raise_for_status,
            read_until_eof=read_until_eof,
            proxy=proxy,
            proxy_auth=proxy_auth,
            timeout=timeout,
            ssl=ssl,
            verify_ssl=verify_ssl,
            fingerprint=fingerprint,
            ssl_context=ssl_context,
            proxy_headers=proxy_headers
        )
    )


def options(
    url: str,
    params: Mapping[str, Any] = None,
    data: Union[aiohttp.FormData, bytes, dict] = None,
    json: JSon = None,
    cookies: Mapping = None,
    headers: Mapping = None,
    skip_auto_headers: Iterable[str] = None,
    auth: aiohttp.BasicAuth = None,
    allow_redirects: bool = True,
    max_redirects: int = 10,
    compress: bool = None,
    chunked: int = None,
    expect100: bool = False,
    raise_for_status: bool = None,
    read_until_eof: bool = True,
    proxy: str = None,
    proxy_auth: aiohttp.BasicAuth = None,
    timeout=aiohttp.client.sentinel,
    ssl: Union[bool, aiohttp.Fingerprint, ssl.SSLContext] = None,
    verify_ssl: bool = None,
    fingerprint: bytes = None,
    ssl_context: ssl.SSLContext = None,
    proxy_headers: Mapping = None
) -> Effect[HasHTTP, ClientError, Response]:
    """

    """
    return get_environment().and_then(
        lambda env: env.http.make_request(
            'options',
            url,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            headers=headers,
            skip_auto_headers=skip_auto_headers,
            auth=auth,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            compress=compress,
            chunked=chunked,
            expect100=expect100,
            raise_for_status=raise_for_status,
            read_until_eof=read_until_eof,
            proxy=proxy,
            proxy_auth=proxy_auth,
            timeout=timeout,
            ssl=ssl,
            verify_ssl=verify_ssl,
            fingerprint=fingerprint,
            ssl_context=ssl_context,
            proxy_headers=proxy_headers
        )
    )


def patch(
    url: str,
    params: Mapping[str, Any] = None,
    data: Union[aiohttp.FormData, bytes, dict] = None,
    json: JSon = None,
    cookies: Mapping = None,
    headers: Mapping = None,
    skip_auto_headers: Iterable[str] = None,
    auth: aiohttp.BasicAuth = None,
    allow_redirects: bool = True,
    max_redirects: int = 10,
    compress: bool = None,
    chunked: int = None,
    expect100: bool = False,
    raise_for_status: bool = None,
    read_until_eof: bool = True,
    proxy: str = None,
    proxy_auth: aiohttp.BasicAuth = None,
    timeout=aiohttp.client.sentinel,
    ssl: Union[bool, aiohttp.Fingerprint, ssl.SSLContext] = None,
    verify_ssl: bool = None,
    fingerprint: bytes = None,
    ssl_context: ssl.SSLContext = None,
    proxy_headers: Mapping = None
) -> Effect[HasHTTP, ClientError, Response]:
    """

    """
    return get_environment().and_then(
        lambda env: env.http.make_request(
            'patch',
            url,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            headers=headers,
            skip_auto_headers=skip_auto_headers,
            auth=auth,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            compress=compress,
            chunked=chunked,
            expect100=expect100,
            raise_for_status=raise_for_status,
            read_until_eof=read_until_eof,
            proxy=proxy,
            proxy_auth=proxy_auth,
            timeout=timeout,
            ssl=ssl,
            verify_ssl=verify_ssl,
            fingerprint=fingerprint,
            ssl_context=ssl_context,
            proxy_headers=proxy_headers
        )
    )
