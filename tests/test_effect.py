from .monad_test import MonadTest
from pfun import effect, compose, identity, either

import pytest
from hypothesis import given, assume
from .strategies import effects, anything, unaries
from .utils import recursion_limit
from unittest import mock


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
            effect.wrap(value).map(h).run(env) ==
            effect.wrap(value).map(g).map(f).run(env)
        )

    @given(anything(), anything())
    def test_identity_law(self, value, env):
        assert (
            effect.wrap(value).map(identity).run(env) ==
            effect.wrap(value).run(env)
        )

    @given(unaries(effects()), anything(), anything())
    def test_left_identity_law(self, f, value, env):
        assert (
            effect.wrap(value).and_then(f).run(env) ==
            f(value).run(env)
        )
    
    @given(anything(), anything())
    def test_right_identity_law(self, value, env):
        assert (
            effect.wrap(value).and_then(
                effect.wrap
            ).run(env) == effect.wrap(value).run(env)
        )

    @given(anything(), anything())
    def test_equality(self, value, env):
        assert effect.wrap(value).run(env
                                      ) == effect.wrap(value).run(env)

    @given(anything(), anything(), anything())
    def test_inequality(self, first, second, env):
        assume(first != second)
        assert effect.wrap(first).run(env
                                      ) != effect.wrap(second).run(env)
    
    def test_get_environment(self):
        assert effect.get_environment().run('env') == 'env'
    
    def test_from_awaitable(self):
        async def f():
            return 1
        
        assert effect.from_awaitable(f()).run(None) == 1
    
    def test_sequence(self):
        assert effect.sequence_async([effect.wrap(v) for v in range(3)]
                              ).run(None) == (0, 1, 2)

    def test_stack_safety(self):
        with recursion_limit(100):
            effect.sequence_async([effect.wrap(v) for v in range(500)]).run(None)

    def test_filter_m(self):
        assert effect.filter_m(lambda v: effect.wrap(v % 2 == 0),
                              range(5)).run(None) == (0, 2, 4)

    def test_map_m(self):
        assert effect.map_m(effect.wrap,
                           range(3)).run(None) == (0, 1, 2)
    
    def test_with_effect(self):
        @effect.with_effect
        def f():
            a = yield effect.wrap(2)
            b = yield effect.wrap(2)
            return a + b

        @effect.with_effect
        def test_stack_safety():
            for _ in range(500):
                yield effect.wrap(1)
            return None

        with recursion_limit(100):
            test_stack_safety().run(None)

        assert f().run(None) == 4
    
    def test_either(self):
        success = effect.wrap(1)
        error = effect.fail('error')
        assert success.either().run(None) == either.Right(1)
        error.either().run(None) == either.Left('error')
    
    def test_recover(self):
        success = effect.wrap(1)
        error = effect.fail('error')
        assert success.recover(lambda e: effect.wrap(2)).run(None) == 1
        assert error.recover(lambda e: effect.wrap(2)).run(None) == 2
    
    def test_absolve(self):
        right = either.Right(1)
        left = either.Left('error')
        right_effect = effect.wrap(right)
        left_effect = effect.wrap(left)
        assert effect.absolve(right_effect).run(None) == 1
        with pytest.raises(Exception):
            # todo
            effect.absolve(left_effect).run(None)
    
    def test_fail(self):
        with pytest.raises(Exception):
            # todo
            effect.fail('error').run(None)
    
    def test_combine(self):
        def f(a, b):
            return a + b
        
        assert effect.combine(effect.wrap('a'), effect.wrap('b'))(f).run(None) == 'ab'
    
    def test_lift(self):
        def f(a, b):
            return a + b
        
        assert effect.lift(f)(effect.wrap('a'), effect.wrap('b')).run(None) == 'ab'
    
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
    return mock.patch('pfun.effect.files.open', mock.mock_open(read_data=read_data))


class TestConsole:
    def test_print_line(self, capsys) -> None:
        
        e = effect.console.print_line('Hello, world!')
        e.run(HasConsole())
        captured = capsys.readouterr()
        assert captured.out == 'Hello, world!\n'
    
    def test_get_line(self) -> None:
        with mock.patch('pfun.effect.console.input', return_value='Hello!') as mocked_input:
            e = effect.console.get_line('Say hello')
            assert e.run(HasConsole()) == 'Hello!'
            mocked_input.assert_called_once_with('Say hello')


class HasFiles:
    files = effect.files.Files()


class TestFiles:
    def test_read(self):
        with mock_open('content') as mocked_open:
            e = effect.files.read('foo.txt')
            assert e.run(HasFiles()) == 'content'

    def test_write(self):
        with mock_open() as mocked_open:
            e = effect.files.write('foo.txt', 'content')
            e.run(HasFiles())
            mocked_open.assert_called_once_with('foo.txt', 'w')
            mocked_open().write.assert_called_once_with('content')
    
    def test_read_bytes(self):
        with mock_open(b'content') as mocked_open:
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
