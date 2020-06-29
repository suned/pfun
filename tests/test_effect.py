from subprocess import CalledProcessError
from unittest import mock

import pytest
from hypothesis import assume, given

from pfun import compose, effect, either, identity

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
        with pytest.raises(Exception):
            # todo
            catched_value_error.run(None)

        with pytest.raises(Exception):
            # todo
            catched_division_error.run(None)


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
