from datetime import timedelta
import itertools
from unittest.mock import Mock

from pfun import schedule, success


two_seconds = timedelta(seconds=2)


def test_spaced():
    deltas = schedule.spaced(two_seconds).run(None)
    assert list(itertools.islice(deltas, 3)) == [two_seconds] * 3


def test_exponential():
    deltas = schedule.exponential(two_seconds).run(None)
    assert list(itertools.islice(deltas, 3)) == [two_seconds, two_seconds * 2, two_seconds * 4]


def test_recurs():
    deltas = schedule.recurs(3, schedule.spaced(two_seconds)).run(None)
    assert list(deltas) == [two_seconds] * 3


def test_take_while():
    deltas = schedule.take_while(
        lambda delta: delta < timedelta(seconds=8),
        schedule.exponential(two_seconds)
    ).run(None)
    assert list(deltas) == [two_seconds, two_seconds * 2]


def test_until():
    deltas = schedule.until(timedelta(seconds=8), schedule.exponential(two_seconds)).run(None)
    assert list(deltas) == [two_seconds, two_seconds * 2]


def test_jitter():
    mock_random = Mock()
    mock_random.random.return_value = success(.5)
    modules = Mock()
    modules.random = mock_random

    deltas = schedule.jitter(schedule.spaced(two_seconds)).run(modules)
    assert list(itertools.islice(deltas, 3)) == [timedelta(seconds=2.5)] * 3

