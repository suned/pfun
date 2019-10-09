import re

from main_dec import main

from pfun.io import read_str, with_effect, IOs


class MalformedTomlError(Exception):
    pass


def get_version(toml: str) -> str:
    match = re.search(r'version = \"([0-9]+\.[0-9]+\.[0-9]+)\"', toml)
    if match is None:
        raise MalformedTomlError('Could not find version in pyproject.toml')
    else:
        return match[1]


@with_effect
def check_version(toml_path: str, expected_version: str) -> IOs[str, None]:
    toml = yield read_str(toml_path)
    actual_version = get_version(toml)
    message = (
        f'version "{actual_version}" in pyproject.toml '
        f'did not match "{expected_version}"'
    )
    assert actual_version == expected_version, message


@main
def run(toml_path: str, expected_version: str) -> None:
    check_version(toml_path, expected_version).run()
