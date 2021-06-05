from typing_extensions import Final

from . import console, files, logging, ref, subprocess  # noqa
from .dict import Dict  # noqa
from .effect import *  # noqa
from .either import Either, Left, Right  # noqa
from .functions import *  # noqa
from .immutable import Immutable  # noqa
from .lens import RootLens
from .list import List  # noqa
from .maybe import Just, Maybe, Nothing  # noqa

lens: Final[RootLens] = RootLens()

try:
    from . import http, sql, hypothesis_strategies  # noqa
except ImportError:
    pass
