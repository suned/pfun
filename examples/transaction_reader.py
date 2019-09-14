from pfun.reader import Reader, value, ask
from pfun import Immutable, curry

from typing import TypeVar, List, Callable


class Transaction:
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

get_transaction: Callable[[], DBAction[Transaction]] = ask


def get_user(user_id: int) -> DBAction[User]:
    return value(User(user_id, 'pa$$word'))


@curry
def check_password(password: str, user: User) -> DBAction[bool]:
    return value(password == user.password)


@curry
def set_password(user_id: int, old_password: str,
                 new_password: str) -> DBAction[bool]:
    @curry
    def update_password(user: User, t: Transaction) -> DBAction[bool]:
        user = user.clone(password=new_password)
        t.add(user)
        return value(True)

    # yapf: disable
    return get_user(user_id).and_then(
        lambda user: check_password(old_password, user).and_then(
            lambda match:
                get_transaction().and_then(update_password(user))
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
