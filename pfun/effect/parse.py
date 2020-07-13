import json as json_
from typing import Any, Dict, Iterable, Union

from .effect import Effect, catch

JSonPrim = Union[int, str, float, Dict[str, Any]]
JSon = Union[Iterable[JSonPrim], JSonPrim]


def json(s: Union[str, bytes]) -> Effect[Any, json_.JSONDecodeError, JSon]:
    return catch(json_.JSONDecodeError)(lambda: json_.loads(s))
