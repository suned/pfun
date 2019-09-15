from unittest.mock import patch, mock_open as mock_open_
import sys
from pfun.io import (
    put_line,
    get_line,
    read_file,
    read_file_bytes,
    write_file,
    write_file_bytes,
    IO,
    Put,
    Get,
    ReadFile,
    WriteFile
)
from pfun import identity, compose
from .monad_test import MonadTest
from .strategies import ios, unaries, anything
from hypothesis import given, assume
from hypothesis.strategies import text


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
            assert IO(value) == IO(value)
            assert IO(value).run() == IO(value).run()
            assert Put((text, io)).run() == Put((text, io)).run()
            assert Get(lambda _: io).run() == Get(lambda _: io).run()
            assert ReadFile((text, lambda _: io)).run() == ReadFile(
                (text, lambda _: io)
            ).run()
            assert WriteFile((text, text, io)).run() == WriteFile(
                (text, text, io)
            ).run()

    @given(ios(), text())
    def test_identity_law(self, io, text):
        with mock_input(), mock_open(text), mock_print():
            assert io.map(identity).run() == io.run()

    @given(anything(), anything(), text())
    def test_inequality(self, value1, value2, text):
        assume(value1 != value2)
        assert IO(value1) != IO(value2)
        assert IO(value1).run() != IO(value2).run()
        # assert Put((text, io1)).run() != Put((text, io2)).run()
        # assert Get(lambda _: io1).run() != Get(lambda _: io2).run()
        # assert ReadFile((text, lambda _: io1)).run() != ReadFile(
        #     (text, lambda _: io2)).run()
        # assert WriteFile((text, text, io1)).run() != WriteFile(
        #     (text, text, io2)).run()

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
            mocked_open.assert_called_with('test.txt', 'r')

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
