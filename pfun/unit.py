from typing import Tuple, Any

Unit = Tuple[()]


def is_unit(v: Any) -> bool:
    return v == ()
