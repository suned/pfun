import re
from typing import Union

from main_dec import main
from pfun import Effect, Try, curry, error, files, success


class MalformedTomlError(Exception):
    pass


class NoVersionMatchError(Exception):
    pass


def get_version(toml: str) -> Try[MalformedTomlError, str]:
    match = re.search(r'version = \"([0-9]+\.[0-9]+\.[0-9]+)\"', toml)
    if match is None:
        return error(
            MalformedTomlError('Could not find version in pyproject.toml')
        )
    else:
        return success(match[1])


@curry
def compare(expected_version: str,
            actual_version: str) -> Try[NoVersionMatchError, None]:
    message = (
        f'version "{actual_version}" in pyproject.toml '
        f'did not match "{expected_version}"'
    )
    if actual_version != expected_version:
        return error(NoVersionMatchError(message))
    return success(None)


def check_version(
    toml_path: str, expected_version: str
) -> Effect[files.HasFiles,
            Union[OSError, MalformedTomlError, NoVersionMatchError],
            None]:
    toml = files.read(toml_path)
    actual_version = toml.and_then(get_version)
    return actual_version.and_then(compare(expected_version))


class Env:
    files = files.Files()


@main
def run(toml_path: str, expected_version: str) -> None:
    check_version(toml_path, expected_version).run(Env())
