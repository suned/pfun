from unittest.mock import Mock

import pytest

from pfun.effect import success
from scripts.check_version import NoVersionMatchError, check_version


def test_check_version_accepts_matching_versions():
    mock_env = Mock()
    mock_env.files.read.return_value = success('version = "1.0.0"')
    check_version('foo.toml', '1.0.0').run(mock_env)


def test_check_version_fails_on_version_mismatch():
    mock_env = Mock()
    mock_env.files.read.return_value = success('version = "1.0.0"')
    with pytest.raises(NoVersionMatchError):
        check_version('foo.toml', '1.0.1').run(mock_env)
