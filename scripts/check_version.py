import re
import sys

from pfun.io import read_str, IO, value


class MalformedTomlError(Exception):
    pass


def get_version(toml: str) -> str:
    match = re.search(r'version = \"([0-9]+\.[0-9]+\.[0-9]+)\"', toml)
    if match is None:
        raise MalformedTomlError('Could not find version in pyproject.toml')
    else:
        return match[1]


def check_version(toml: str) -> IO[None]:
    actual_version = get_version(toml)
    expected_version = sys.argv[2]
    assert actual_version == expected_version, f'version "{actual_version}"" in pyproject.toml did not match "{expected_version}""'
    return value(None)


if __name__ == '__main__':
    read_str(sys.argv[1]).and_then(check_version).run()
