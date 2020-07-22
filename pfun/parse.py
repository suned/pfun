import json as json_
from typing import Any, Dict, Iterable, Union

from .effect import Try, add_repr, catch

JSonPrim = Union[int, str, float, Dict[str, Any]]
JSon = Union[Iterable[JSonPrim], JSonPrim]


@add_repr
def json(s: Union[str, bytes]) -> Try[json_.JSONDecodeError, JSon]:
    return catch(json_.JSONDecodeError)(lambda: json_.loads(s))
