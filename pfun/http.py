from __future__ import annotations

import http
import json
import ssl
from typing import Any, Callable
from typing import Dict as Dict_
from typing import Iterable, Mapping, NoReturn, Union

from typing_extensions import Protocol

from .dict import Dict
from .effect import (Depends, Effect, Resource, Try, add_repr, depend, error,
                     success)
from .either import Right
from .functions import curry
from .immutable import Immutable
from .maybe import Maybe, from_optional

try:
    import aiohttp
    from aiohttp.client_exceptions import ClientError
except ImportError:
    raise ImportError(
        'Could not import aiohttp. To use pfun.http, '
        'install pfun with \n\n\tpip install pfun[http]'
    )

JSonPrim = Union[int, str, float, Dict_[str, Any]]
JSon = Union[Iterable[JSonPrim], JSonPrim]


class Response(Immutable):
    """
    The result of making a HTTP request.
    """
    content: bytes
    """
    The response content
    """
    status: int
    """
    The request status
    """
    reason: Maybe[str]
    """
    The reason for the request status, e.g "OK"
    """
    cookies: http.cookies.BaseCookie
    """
    The response cookies
    """
    headers: Dict[str, str]
    """
    The response headers
    """
    links: Dict[str, str]
    """
    The response http link header
    """
    encoding: Maybe[str]
    """
    Encoding of the response content if present in the header
    or if detectable by chardet
    """


class HTTP(Immutable, init=False):
    """
    Module for making HTTP requests.
    """
    session: Resource[NoReturn, aiohttp.ClientSession]

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
        """
        All keyword arguments are passed \
        to the wrapped `aiohttp.ClientSession`. Refer to the originial \
        documentation for their meaning.
        """
        object.__setattr__(
            self,
            'session',
            Resource(
                lambda: Right(
                    aiohttp.ClientSession(
                        connector=connector,
                        cookies=cookies,
                        headers=headers,
                        skip_auto_headers=skip_auto_headers,
                        auth=auth,
                        json_serialize=json_serialize,
                        version=version,
                        cookie_jar=cookie_jar,
                        read_timeout=read_timeout,
                        conn_timeout=conn_timeout,
                        timeout=timeout,
                        raise_for_status=raise_for_status,
                        connector_owner=connector_owner,
                        auto_decompress=auto_decompress,
                        requote_redirect_url=requote_redirect_url,
                        trust_env=trust_env,
                        trace_configs=(
                            trace_configs
                            if trace_configs is None else list(trace_configs)
                        )
                    )
                )
            )
        )

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
    ) -> Try[ClientError, Response]:
        """
        Make a request using HTTP verb `method` to URL `url`. All keyword
        arguments are passed to `aiohttp.ClientSession.request`. Refer
        to the original documentation for their meaning.

        Example:
            >>> http = HTTP()
            >>> http.make_request('get', 'http://foo.com')(None)
            Response(...)

        Args:
            method: HTTP method to use. One of `get`, `put`, `post`, \
                `delete`, `patch`, `head` or `option`.
            url: target URL for the request
        Return:
            `Effect` that produces a `Response`
        """
        async def _make_request(session: aiohttp.ClientSession
                                ) -> Try[ClientError, Response]:
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
                            Dict(
                                {
                                    k: str(response.links[k])
                                    for k in response.links
                                }
                            ),
                            from_optional(response.charset)
                        )
                    )
            except ClientError as e:
                return error(e)

        return self.session.get().and_then(_make_request)


class HasHTTP(Protocol):
    """
    Module provider providing the `http` module
    """
    http: HTTP
    """
    The provided `HTTP` module
    """


@add_repr
def get_session() -> Depends[HasHTTP, aiohttp.ClientSession]:
    """
    Get an effect that produces an `aiohttp.ClientSession`.
    Use this if you need features of `aiohttp` that are not supported
    by the high-level api.

    Example:
        >>> async def use_session(session: aiohttp.ClientSession) -> str:
        ...     async with session.get('http://www.google.com') as response:
        ...         return await response.text()
        >>> class Env:
        ...     http = HTTP()
        >>> get_session().map(use_session).run(Env())
        "<!doctype html> ..."

    Return:
        `Effect` that succeeds with `aiohttp.ClientSession`
    """
    return depend(HasHTTP).and_then(lambda env: env.http.session.get())


@curry
@add_repr
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
    Make a HTTP `get` request to URL `url`. All keyword
    arguments are passed to `aiohttp.ClientSession.request`. Refer
    to the original documentation for their meaning.

    Example:
        >>> class Env:
        ...     http = HTTP()
        >>> get('http://foo.com')(Env())
        Response(...)

    Args:
        url: target URL for the request
    Return:
        `Effect` that produces a `Response`
    """
    return depend(HasHTTP).and_then(
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


@curry
@add_repr
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
    Make a HTTP `put` request to URL `url`. All keyword
    arguments are passed to `aiohttp.ClientSession.request`. Refer
    to the original documentation for their meaning.

    Example:
        >>> class Env:
        ...     http = HTTP()
        >>> put('http://foo.com')(Env())
        Response(...)

    Args:
        url: target URL for the request
    Return:
        `Effect` that produces a `Response`
    """
    return depend().and_then(
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


@curry
@add_repr
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
    Make a HTTP `post` request to URL `url`. All keyword
    arguments are passed to `aiohttp.ClientSession.request`. Refer
    to the original documentation for their meaning.

    Example:
        >>> class Env:
        ...     http = HTTP()
        >>> post('http://foo.com')(Env())
        Response(...)

    Args:
        url: target URL for the request
    Return:
        `Effect` that produces a `Response`
    """
    return depend(HasHTTP).and_then(
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


@curry
@add_repr
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
    Make a HTTP `delete` request to URL `url`. All keyword
    arguments are passed to `aiohttp.ClientSession.request`. Refer
    to the original documentation for their meaning.

    Example:
        >>> class Env:
        ...     http = HTTP()
        >>> delete('http://foo.com')(Env())
        Response(...)

    Args:
        url: target URL for the request
    Return:
        `Effect` that produces a `Response`
    """
    return depend(HasHTTP).and_then(
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


@curry
@add_repr
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
    Make a HTTP `head` request to URL `url`. All keyword
    arguments are passed to `aiohttp.ClientSession.request`. Refer
    to the original documentation for their meaning.

    Example:
        >>> class Env:
        ...     http = HTTP()
        >>> head('http://foo.com')(Env())
        Response(...)

    Args:
        url: target URL for the request
    Return:
        `Effect` that produces a `Response`
    """
    return depend(HasHTTP).and_then(
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


@curry
@add_repr
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
    Make a HTTP `options` request to URL `url`. All keyword
    arguments are passed to `aiohttp.ClientSession.request`. Refer
    to the original documentation for their meaning.

    Example:
        >>> class Env:
        ...     http = HTTP()
        >>> options('http://foo.com')(Env())
        Response(...)

    Args:
        url: target URL for the request
    Return:
        `Effect` that produces a `Response`
    """
    return depend(HasHTTP).and_then(
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


@curry
@add_repr
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
    Make a HTTP `patch` request to URL `url`. All keyword
    arguments are passed to `aiohttp.ClientSession.request`. Refer
    to the original documentation for their meaning.

    Example:
        >>> class Env:
        ...     http = HTTP()
        >>> patch('http://foo.com')(Env())
        Response(...)

    Args:
        url: target URL for the request
    Return:
        `Effect` that produces a `Response`
    """
    return depend(HasHTTP).and_then(
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
