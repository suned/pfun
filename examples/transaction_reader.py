from pfun.reader import Reader, value
from pfun import Immutable, curry

from typing import TypeVar, List


class Transaction(Immutable):
    _os: List[object] = []

    def add(self, o: object) -> None:
        self._os.append(o)  # Nothing to see here...

    def commit(self) -> bool:
        print('commited ', self._os)  # ...Or here...
        return True

    def rollback(self) -> bool:
        ...


class User(Immutable):
    user_id: int
    password: str


A = TypeVar('A')
DBAction = Reader[Transaction, A]


def get_user(user_id: int) -> DBAction[User]:
    return value(User(user_id, 'pa$$word'))


@curry
def check_password(password: str, user: User) -> DBAction[bool]:
    return value(password == user.password)


@curry
def set_password(user_id: int, old_password: str,
                 new_password: str) -> DBAction[bool]:
    @curry
    def update_password(user: User, t: Transaction) -> bool:
        user = user.clone(password=new_password)
        t.add(user)
        return True

    # yapf: disable
    return get_user(user_id).and_then(
        lambda user: check_password(old_password, user).and_then(
            lambda match: DBAction(update_password(user))
            if match
            else value(False)
        )
    )
    # yapf: enable


def run(action: DBAction[A]) -> A:
    t = Transaction()
    try:
        result = action.run(t)
        t.commit()
        return result
    except Exception:
        t.rollback()
        raise
