import os
import pytest

from mypy import api as mypy_api

parametrize = pytest.mark.parametrize


def python_files(path):
    py_files = []
    current_folder, _ = os.path.split(__file__)
    folder = os.path.join(current_folder, path)
    for root, _, files in os.walk(folder):
        for file in files:
            if file == '__init__.py':
                continue
            if file.endswith('.py'):
                py_files.append(os.path.join(root, file))
    return py_files


def type_check(file):
    return mypy_api.run(['--config-file=tests/mypy.ini', file])


@parametrize('file', python_files('type_tests/positives'))
def test_positives(file):
    normal_report, error_report, exit_code = type_check(file)
    if normal_report or error_report or exit_code != 0:
        pytest.fail(error_report)


@parametrize('file', python_files('type_tests/negatives'))
def test_negatives(file):
    normal_report, error_report, exit_code = type_check(file)
    if not normal_report or exit_code == 0:
        pytest.fail('No type error emitted for {}'.format(file))
