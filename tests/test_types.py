import os
import subprocess
import pytest


parametrize = pytest.mark.parametrize


def python_files(path):
    py_files = []
    current_folder, _ = os.path.split(__file__)
    folder = os.path.join(current_folder, path)
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith('.py'):
                py_files.append(os.path.join(root, file))
    return py_files


def type_check(file):
    p = subprocess.run(['mypy', file], stdout=subprocess.PIPE)
    return p.stdout.decode()


@pytest.mark.skip
@parametrize('file', python_files('type_tests/positives'))
def test_positives(file):
    output = type_check(file)
    if output:
        pytest.fail(output)


@pytest.mark.skip
@parametrize('file', python_files('type_tests/negatives'))
def test_negatives(file):
    output = type_check(file)
    if not output:
        pytest.fail('No type error emitted for {}'.format(file))
