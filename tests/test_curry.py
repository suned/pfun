from pfun import curry


def f(
    pos_1: str,
    pos_2: str,
    *args: str,
    optional_1='default_1',
    optional_2='default_2',
    **kwargs
) -> dict:
    return {
        'pos_1': pos_1,
        'pos_2': pos_2,
        '*args': args,
        'optional_1': optional_1,
        'optional_2': optional_2,
        '**kwargs': kwargs
    }


def test_positional():
    assert curry(f)('pos_1')('pos_2') == {
        'pos_1': 'pos_1',
        'pos_2': 'pos_2',
        '*args': (),
        'optional_1': 'default_1',
        'optional_2': 'default_2',
        '**kwargs': {}
    }


def test_variadic():
    assert curry(f)('pos_1')('pos_2', 'varg_1', 'varg_2') == {
        'pos_1': 'pos_1',
        'pos_2': 'pos_2',
        '*args': ('varg_1', 'varg_2'),
        'optional_1': 'default_1',
        'optional_2': 'default_2',
        '**kwargs': {}
    }


def test_optional():
    assert curry(f)(
        optional_1='v1',
        optional_2='v2',
        kwarg='kwarg'
    )('pos_1')('pos_2', 'varg_1', 'varg_2') == {
        'pos_1': 'pos_1',
        'pos_2': 'pos_2',
        '*args': ('varg_1', 'varg_2'),
        'optional_1': 'v1',
        'optional_2': 'v2',
        '**kwargs': {'kwarg': 'kwarg'}
    }


def test_optional_only():
    def g(a='', b=''):
        return a, b

    assert curry(g)(a='a', b='b') == ('a', 'b')
