import sys
from unittest.mock import mock_open as mock_open_
from unittest.mock import patch

from hypothesis import assume, given
from hypothesis.strategies import text

from pfun import compose, identity
from pfun.io import filter_m, get_line, map_m, put_line
from pfun.io import read_bytes as read_file_bytes
from pfun.io import read_str as read_file
from pfun.io import sequence
from pfun.io import value as IO
from pfun.io import with_effect
from pfun.io import write_bytes as write_file_bytes
from pfun.io import write_str as write_file

from .monad_test import MonadTest
from .strategies import anything, ios, unaries
from .utils import recursion_limit


def mock_input():
    return patch('pfun.io.input')


def mock_print():
    return patch('pfun.io.print')


def mock_open(read_data=None):
    return patch('pfun.io.open', mock_open_(read_data=read_data))


class TestIO(MonadTest):
    @given(ios(), text())
    def test_right_identity_law(self, io, open_data):
        with mock_input(), mock_open(open_data), mock_print():
            assert io.and_then(IO).run() == io.run()

    @given(anything(), unaries(ios()), text())
    def test_left_identity_law(self, value, f, open_data):
        with mock_input(), mock_open(open_data), mock_print():
            assert IO(value).and_then(f).run() == f(value).run()

    @given(ios(), unaries(ios()), unaries(ios()), text())
    def test_associativity_law(self, io, f, g, open_data):
        with mock_input(), mock_open(open_data), mock_print():
            assert io.and_then(f).and_then(g).run(
            ) == io.and_then(lambda x: f(x).and_then(g)).run()

    @given(ios(), unaries(), unaries(), text())
    def test_composition_law(self, io, f, g, text):
        h = compose(f, g)
        with mock_input(), mock_open(text), mock_print():
            assert io.map(h).run() == io.map(g).map(f).run()

    @given(anything(), ios(), text())
    def test_equality(self, value, io, text):
        with mock_input(), mock_open(text), mock_print():
            assert IO(value).run() == IO(value).run()

    @given(ios(), text())
    def test_identity_law(self, io, text):
        with mock_input(), mock_open(text), mock_print():
            assert io.map(identity).run() == io.run()

    @given(anything(), anything(), text())
    def test_inequality(self, value1, value2, text):
        assume(value1 != value2)
        assert IO(value1).run() != IO(value2).run()

    def test_get_line(self):
        with mock_input() as mocked_input:
            mocked_input.return_value = 'Hello'
            assert get_line().run() == 'Hello'

    def test_put_line(self):
        with mock_print() as mocked_print:
            put_line('Hello').run()
            mocked_print.assert_called_with('Hello', file=sys.stdout)

    def test_read_file(self):
        with mock_open('Hello') as mocked_open:
            assert read_file('test.txt').run() == 'Hello'
            mocked_open.assert_called_with('test.txt')

    def test_read_file_bytes(self):
        with mock_open(b'Hello') as mocked_open:
            assert read_file_bytes('test.txt').run() == b'Hello'
            mocked_open.assert_called_with('test.txt', 'rb')

    def test_write_file(self):
        with mock_open() as mocked_open:
            write_file('test.txt')('Hello').run()
            mocked_open.assert_called_with('test.txt', 'w')
            mocked_open().write.assert_called_with('Hello')

    def test_write_file_bytes(self):
        with mock_open() as mocked_open:
            write_file_bytes('test.txt')(b'Hello').run()
            mocked_open.assert_called_with('test.txt', 'wb')
            mocked_open().write.assert_called_with(b'Hello')

    def test_with_effect(self):
        @with_effect
        def f():
            a = yield IO(2)
            b = yield IO(2)
            return a + b

        assert f().run() == 4

        @with_effect
        def test_stack_safety():
            for _ in range(500):
                yield IO(1)
            return None

        with recursion_limit(100):
            test_stack_safety().run()

    def test_sequence(self):
        assert sequence([IO(v) for v in range(3)]).run() == (0, 1, 2)

    def test_stack_safety(self):
        with recursion_limit(100):
            sequence([IO(v) for v in range(500)]).run()

    def test_filter_m(self):
        assert filter_m(lambda v: IO(v % 2 == 0), range(3)).run() == (0, 2)

    def test_map_m(self):
        assert map_m(IO, range(3)).run() == (0, 1, 2)
