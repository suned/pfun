from subprocess import CalledProcessError
from unittest import mock

import aiohttp
import asynctest
import pytest
from hypothesis import assume, given

from pfun import compose, effect, either, identity
from pfun.effect.effect import Environment, Resource

from .monad_test import MonadTest
from .strategies import anything, effects, unaries
from .utils import recursion_limit


class TestEffect(MonadTest):
    @given(effects(), unaries(effects()), unaries(effects()), anything())
    def test_associativity_law(self, e, f, g, env):
        assert (
            e.and_then(f).and_then(g).run(env) ==
            e.and_then(lambda x: f(x).and_then(g)).run(env)
        )

    @given(unaries(), unaries(), anything(), anything())
    def test_composition_law(self, f, g, value, env):
        h = compose(f, g)
        assert (
            effect.success(value).map(h).run(env) ==
            effect.success(value).map(g).map(f).run(env)
        )

    @given(anything(), anything())
    def test_identity_law(self, value, env):
        assert (
            effect.success(value).map(identity).run(env) ==
            effect.success(value).run(env)
        )

    @given(unaries(effects()), anything(), anything())
    def test_left_identity_law(self, f, value, env):
        assert (
            effect.success(value).and_then(f).run(env) == f(value).run(env)
        )

    @given(anything(), anything())
    def test_right_identity_law(self, value, env):
        assert (
            effect.success(value).and_then(
                effect.success
            ).run(env) == effect.success(value).run(env)
        )

    @given(anything(), anything())
    def test_equality(self, value, env):
        assert effect.success(value).run(env) == effect.success(value).run(env)

    @given(anything(), anything(), anything())
    def test_inequality(self, first, second, env):
        assume(first != second)
        assert effect.success(first).run(env) != effect.success(second
                                                                ).run(env)

    def test_get_environment(self):
        assert effect.get_environment().run('env') == 'env'

    def test_from_awaitable(self):
        async def f():
            return 1

        assert effect.from_awaitable(f()).run(None) == 1

    def test_sequence(self):
        assert effect.sequence_async([effect.success(v) for v in range(3)]
                                     ).run(None) == (0, 1, 2)

    def test_stack_safety(self):
        with recursion_limit(100):
            effect.sequence_async([effect.success(v)
                                   for v in range(500)]).run(None)

        e = effect.error('')
        for _ in range(500):
            e = e.recover(lambda _: effect.error(''))
        e = e.recover(lambda _: effect.success(''))
        with recursion_limit(100):
            e.run(None)

        e = effect.success('')
        for _ in range(500):
            e = e.either()
        with recursion_limit(100):
            e.run(None)

    def test_filter_m(self):
        assert effect.filter_m(lambda v: effect.success(v % 2 == 0),
                               range(5)).run(None) == (0, 2, 4)

    def test_map_m(self):
        assert effect.map_m(effect.success, range(3)).run(None) == (0, 1, 2)

    def test_with_effect(self):
        @effect.with_effect
        def f():
            a = yield effect.success(2)
            b = yield effect.success(2)
            return a + b

        @effect.with_effect
        def test_stack_safety():
            for _ in range(500):
                yield effect.success(1)
            return None

        with recursion_limit(100):
            test_stack_safety().run(None)

        assert f().run(None) == 4

    def test_either(self):
        success = effect.success(1)
        error = effect.error('error')
        assert success.either().run(None) == either.Right(1)
        error.either().run(None) == either.Left('error')

    def test_recover(self):
        success = effect.success(1)
        error = effect.error('error')
        assert success.recover(lambda e: effect.success(2)).run(None) == 1
        assert error.recover(lambda e: effect.success(2)).run(None) == 2

    def test_absolve(self):
        right = either.Right(1)
        left = either.Left('error')
        right_effect = effect.success(right)
        left_effect = effect.success(left)
        assert effect.absolve(right_effect).run(None) == 1
        with pytest.raises(Exception):
            # todo
            effect.absolve(left_effect).run(None)

    def test_error(self):
        with pytest.raises(Exception):
            # todo
            effect.error('error').run(None)

    def test_combine(self):
        def f(a, b):
            return a + b

        assert effect.combine(effect.success('a'),
                              effect.success('b'))(f).run(None) == 'ab'

    def test_catch(self):
        def f(fail):
            if fail:
                raise ValueError()
            else:
                return 1

        assert effect.catch(ValueError)(lambda: f(False)).run(None) == 1
        catched_error = effect.catch(ValueError)(lambda: f(True))
        with pytest.raises(Exception):
            # todo
            catched_error.run(None)
        with pytest.raises(ValueError):
            effect.catch(ZeroDivisionError)(lambda: f(True))

    def test_catch_all(self):
        def f(value_error):
            if value_error:
                raise ValueError()
            else:
                raise ZeroDivisionError()

        catched_value_error = effect.catch_all(lambda: f(True))
        catched_division_error = effect.catch_all(lambda: f(False))
        with pytest.raises(ValueError):
            catched_value_error.run(None)

        with pytest.raises(ZeroDivisionError):
            catched_division_error.run(None)

    def test_and_then_with_resources(self):
        resource_1 = Resource(asynctest.MagicMock())
        resource_2 = Resource(asynctest.MagicMock())
        r1, r2 = resource_1.get().and_then(
            lambda r1: resource_2.get().map(lambda r2: (r1, r2))
        )(None)
        resource_1.resource_factory.assert_called_once()
        resource_2.resource_factory.assert_called_once()
        assert resource_1.resource_factory.return_value == r1
        assert resource_2.resource_factory.return_value == r2

    def test_either_with_resource(self):
        resource = Resource(asynctest.MagicMock())
        assert resource.get().either()(None) == either.Right(
            resource.resource_factory.return_value
        )

    def test_recover_with_resources(self):
        resource_1 = Resource(asynctest.MagicMock())
        resource_2 = Resource(asynctest.MagicMock())
        r1, r2 = resource_1.get().and_then(
            lambda r1: effect.error('whoops').recover(
                lambda _: resource_2.get().map(lambda r2: (r1, r2))
            )
        )(None)
        resource_1.resource_factory.assert_called_once()
        resource_2.resource_factory.assert_called_once()
        assert resource_1.resource_factory.return_value == r1
        assert resource_2.resource_factory.return_value == r2

    def test_map_with_resource(self):
        resource = Resource(asynctest.MagicMock())
        r = resource.get().map(identity)(None)
        assert r == resource.resource_factory.return_value

    def test_sequence_async_with_resources(self):
        resource_1 = Resource(asynctest.MagicMock())
        resource_2 = Resource(asynctest.MagicMock())
        r1, r2 = effect.sequence_async(
            (resource_1.get(), resource_2.get())
        )(None)
        resource_1.resource_factory.assert_called_once()
        resource_2.resource_factory.assert_called_once()
        assert resource_1.resource_factory.return_value == r1
        assert resource_2.resource_factory.return_value == r2

    def test_filter_m_with_resources(self):
        resource = Resource(asynctest.MagicMock())
        effect.filter_m(
            lambda v: resource.get().
            discard_and_then(effect.success(v % 2 == 0)), (1, 2, 3)
        )(None)
        resource.resource_factory.return_value.__aenter__.assert_called_once()


class TestResoure:
    def test_get(self):
        resource = Resource(asynctest.MagicMock())
        effect = resource.get()
        assert effect.resource == resource
        assert effect(None) == resource.resource_factory.return_value
        resource.resource_factory.return_value.__aenter__.assert_called_once()
        assert resource.resource is None

    def test_resources_are_unique(self):
        resource = Resource(asynctest.MagicMock())
        r1, r2 = effect.sequence_async((resource.get(), resource.get()))(None)
        assert r1 is r2
        resource.resource_factory.return_value.__aenter__.assert_called_once()


class TestEnvironment:
    @pytest.mark.asyncio
    async def test_add_resource(self):
        exit_stack_mock = asynctest.MagicMock()
        exit_stack_mock.enter_async_context = asynctest.CoroutineMock()
        environment = Environment(None, exit_stack_mock)
        assert (await environment.add_resource(None)) is environment
        exit_stack_mock.enter_async_context.assert_not_awaited()
        resource = Resource(asynctest.MagicMock)
        new_environment = await environment.add_resource(resource)
        assert new_environment is not environment
        assert new_environment.exit_stack is environment.exit_stack
        assert new_environment.resources == set([resource])
        exit_stack_mock.enter_async_context.assert_awaited_once()
        assert (
            await new_environment.add_resource(resource)
        ) is new_environment
        exit_stack_mock.enter_async_context.assert_awaited_once()


class HasConsole:
    console = effect.console.Console()


def mock_open(read_data=None):
    return mock.patch(
        'pfun.effect.files.open', mock.mock_open(read_data=read_data)
    )


class TestConsole:
    def test_print_line(self, capsys) -> None:

        e = effect.console.print_line('Hello, world!')
        e.run(HasConsole())
        captured = capsys.readouterr()
        assert captured.out == 'Hello, world!\n'

    def test_get_line(self) -> None:
        with mock.patch(
            'pfun.effect.console.input', return_value='Hello!'
        ) as mocked_input:
            e = effect.console.get_line('Say hello')
            assert e.run(HasConsole()) == 'Hello!'
            mocked_input.assert_called_once_with('Say hello')


class HasFiles:
    files = effect.files.Files()


class TestFiles:
    def test_read(self):
        with mock_open('content'):
            e = effect.files.read('foo.txt')
            assert e.run(HasFiles()) == 'content'

    def test_write(self):
        with mock_open() as mocked_open:
            e = effect.files.write('foo.txt', 'content')
            e.run(HasFiles())
            mocked_open.assert_called_once_with('foo.txt', 'w')
            mocked_open().write.assert_called_once_with('content')

    def test_read_bytes(self):
        with mock_open(b'content'):
            e = effect.files.read_bytes('foo.txt')
            assert e.run(HasFiles()) == b'content'

    def test_write_bytes(self):
        with mock_open() as mocked_open:
            e = effect.files.write_bytes('foo.txt', b'content')
            e.run(HasFiles())
            mocked_open.assert_called_once_with('foo.txt', 'wb')
            mocked_open().write.assert_called_once_with(b'content')

    def test_append(self):
        with mock_open() as mocked_open:
            e = effect.files.append('foo.txt', 'content')
            e.run(HasFiles())
            mocked_open.assert_called_once_with('foo.txt', 'a+')
            mocked_open().write.assert_called_once_with('content')

    def test_append_bytes(self):
        with mock_open() as mocked_open:
            e = effect.files.append_bytes('foo.txt', b'content')
            e.run(HasFiles())
            mocked_open.assert_called_once_with('foo.txt', 'ab+')
            mocked_open().write.assert_called_once_with(b'content')


class TestRef:
    def test_get(self):
        ref = effect.ref.Ref(0)
        assert ref.get().run(None) == 0

    def test_put(self):
        ref = effect.ref.Ref(0)
        ref.put(1).run(None)
        assert ref.value == 1

    def test_modify(self):
        ref = effect.ref.Ref(0)
        ref.modify(lambda _: 1).run(None)
        assert ref.value == 1

    def test_try_modify(self):
        ref = effect.ref.Ref(0)
        ref.try_modify(lambda _: either.Left('')).either().run(None)
        assert ref.value == 0
        ref.try_modify(lambda _: either.Right(1)).run(None)
        assert ref.value == 1


class HasSubprocess:
    subprocess = effect.subprocess.Subprocess()


class TestSubprocess:
    def test_run_in_shell(self):
        stdout, stderr = effect.subprocess.run_in_shell(
            'echo "test"'
        ).run(
            HasSubprocess()
        )
        assert stdout == b'test\n'

        with pytest.raises(CalledProcessError):
            effect.subprocess.run_in_shell('exit 1').run(HasSubprocess())


class HasLogging:
    logging = effect.logging.Logging()


class TestLogging:
    @mock.patch('pfun.effect.logging.logging')
    def test_get_logger(self, mock_logging):
        effect.logging.get_logger('foo').run(HasLogging())
        mock_logging.getLogger.assert_called_once_with('foo')

    @mock.patch('pfun.effect.logging.logging')
    @pytest.mark.parametrize(
        'log_method',
        ['debug', 'info', 'warning', 'error', 'critical', 'exception']
    )
    def test_logger_methods(self, mock_logging, log_method):
        effect.logging.get_logger('foo').and_then(
            lambda logger: getattr(logger, log_method)('test')
        ).run(HasLogging())
        exc_and_stack_info = log_method == 'exception'
        getattr(
            mock_logging.getLogger('foo'),
            log_method
        ).assert_called_once_with(
            'test', exc_info=exc_and_stack_info, stack_info=exc_and_stack_info
        )  # yapf: disable

    @mock.patch('pfun.effect.logging.logging')
    @pytest.mark.parametrize(
        'log_method',
        ['debug', 'info', 'warning', 'error', 'critical', 'exception']
    )
    def test_logging_methods(self, mock_logging, log_method):
        getattr(effect.logging, log_method)('test').run(HasLogging())
        exc_and_stack_info = log_method == 'exception'
        getattr(mock_logging, log_method).assert_called_once_with(
            'test', exc_info=exc_and_stack_info, stack_info=exc_and_stack_info
        )


class HasHTTP:
    http = effect.http.HTTP()


async def get_awaitable(value):
    return value


class TestHTTP:
    default_params = {
        'params': None,
        'data': None,
        'json': None,
        'cookies': None,
        'headers': None,
        'skip_auto_headers': None,
        'auth': None,
        'allow_redirects': True,
        'max_redirects': 10,
        'compress': None,
        'chunked': None,
        'expect100': False,
        'raise_for_status': None,
        'read_until_eof': True,
        'proxy': None,
        'proxy_auth': None,
        'timeout': aiohttp.client.sentinel,
        'ssl': None,
        'verify_ssl': None,
        'fingerprint': None,
        'ssl_context': None,
        'proxy_headers': None
    }

    def test_get_session(self):
        with asynctest.patch(
            'pfun.effect.http.aiohttp.ClientSession'
        ) as session:
            assert effect.http.get_session()(HasHTTP()) == session()

    @pytest.mark.parametrize(
        'method', ['get', 'put', 'post', 'delete', 'patch', 'head', 'options']
    )
    def test_http_methods(self, method):
        with asynctest.patch(
            'pfun.effect.http.aiohttp.ClientSession'
        ) as session:
            read_mock = asynctest.CoroutineMock()
            read_mock.return_value = b'test'
            (
                session.return_value.request.return_value.__aenter__.
                return_value.read
            ) = read_mock
            assert getattr(effect.http,
                           method)('foo.com')(HasHTTP()).content == b'test'
            session().request.assert_called_once_with(
                method, 'foo.com', **self.default_params
            )
