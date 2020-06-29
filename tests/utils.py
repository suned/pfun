import sys
from contextlib import contextmanager


@contextmanager
def recursion_limit(n):
    recursion_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(n)
    yield
    sys.setrecursionlimit(recursion_limit)
