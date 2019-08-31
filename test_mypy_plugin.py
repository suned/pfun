from pfun.result import Ok, Error, Result
from typing_extensions import Literal
from typing import overload, Union, Any


@overload
def read_file(path: str, mode: Literal['t']) -> Result[str, Exception]:
    ...


@overload
def read_file(path: str, mode: Literal['b']) -> Result[bytes, Exception]:
    ...


def read_file(path: str,
              mode: Literal['t', 'b'] = 't'
              ) -> Union[Result[str, Exception], Result[bytes, Exception]]:
    result: Result[Any, Exception]
    try:
        with open(path) as f:
            result = Ok(f.read())
            return result
    except Exception as e:
        result = Error(e)
    return result


read_file('', 'b')
