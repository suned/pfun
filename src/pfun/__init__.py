from __future__ import annotations

from . import clock, console, files, logging, random, state, subprocess  # noqa
from .dict import Dict  # noqa
from .effect import *  # noqa
from .either import Either, Left, Right  # noqa
from .functions import *  # noqa
from .immutable import Immutable  # noqa
from .lens import *  # noqa
from .list import List  # noqa
from .maybe import Just, Maybe, Nothing  # noqa

try:
    from . import http, sql, hypothesis_strategies  # noqa
except ImportError:
    pass


class _IntersectionMeta(type):
    def __getitem__(self, item):
        return self


class Intersection(metaclass=_IntersectionMeta):
    """
    Abstract type that represents the intersection between two or more
    protocols when using the pfun MyPy plugin.

    Only protocols can be used as arguments to Intersection.

    Example:
        >>> from typing import Protocol
        >>> class P1(Protocol):
        ...     x: str
        >>> class P2(Protocol):
        ...     y: int
        >>> i: Intersection[P1, P2]
        >>> class C:
        ...     x: str
        >>> i = C()  # MyPy error
    """
    pass


class DefaultModules:
    """
    Module provider that provides live implementations
    of default pfun modules.

    Example:
        >>> from pfun import console, random, DefaultModules
        >>> random.random().and_then(console.print_line).run(DefaultModules())
        0.51351531
    Attributes:
        files: The files module
        console: The console module
        random: The random module
        clock: The clock module
        logging: The logging module
        subprocess: The subprocess module
    """
    files: 'files.Files'
    console: 'console.Console'
    random: 'random.Random'
    clock: 'clock.Clock'
    logging: 'logging.Logging'
    subprocess: 'subprocess.Subprocess'

    def __init__(self):
        self.files = files.Files()
        self.console = console.Console()
        self.random = random.Random()
        self.clock = clock.Clock()
        self.logging = logging.Logging()
        self.subprocess = subprocess.Subprocess()
