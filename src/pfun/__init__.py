from typing_extensions import Protocol

from . import console, files, logging, ref, subprocess  # noqa
from .dict import Dict  # noqa
from .effect import *  # noqa
from .either import Either, Left, Right  # noqa
from .functions import *  # noqa
from .immutable import Immutable  # noqa
from .lens import *  # noqa
from .list import List  # noqa
from .maybe import Just, Maybe, Nothing  # noqa
from . import random, console, clock, files

try:
    from . import http, sql, hypothesis_strategies  # noqa
except ImportError:
    pass


class Intersection(Protocol):
    pass


class DefaultModules(Immutable):
    files = files.Files()
    console = console.Console()
    random = random.Random()
    clock = clock.Clock()
