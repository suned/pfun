from pfun.maybe import Maybe, Just


def test_just() -> Maybe[str]:
    return Just(1).and_then(lambda a: Just(str(a)))


# TODO
# def test_nothing() -> Maybe[str]:
#     return Nothing().and_then(lambda a: Just(''))
