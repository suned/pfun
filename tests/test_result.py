from pfun.result import Error, Ok, result


def test_result_decorator():
    to_int = result(int)
    assert to_int('1') == Ok(1)
    error = to_int('Whoops')
    assert isinstance(error, Error)
    assert isinstance(error.get, ValueError)
