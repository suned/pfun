from typing import TypeVar, Generic, Dict as Dict_, Union

from .maybe import Maybe, Nothing, Just
from .immutable import Immutable

K = TypeVar('K')
V = TypeVar('V')


class Dict(Immutable, Generic[K, V], init=False):
    """
    Immutable dictionary class with functional helper methods
    """

    _d: Dict_[K, V]

    def __init__(self, d: Union[Dict_[K, V], 'Dict[K, V]'] = dict()):
        if isinstance(d, Dict):
            d = d._d
        object.__setattr__(self, '_d', dict(d))

    def __repr__(self):
        return f'Dict({repr(self._d)})'

    def __eq__(self, other):
        if isinstance(other, dict):
            return other == self._d
        if isinstance(other, Dict):
            return other._d == self._d
        return False

    def keys(self):
        return self._d.keys()

    def values(self):
        return self._d.values()

    def copy(self):
        return Dict(self._d.copy())

    def items(self):
        return self._d.items()

    def __contains__(self, key: K) -> bool:
        return key in self._d

    def __getitem__(self, key: K) -> Maybe[V]:
        """
        get the value associated with a key

        :example:
        >>> Dict(key='value')['key']
        Just('value')

        :param key: the key to retrieve
        :return: value associated with key
        """
        return self.get(key)

    def set(self, key: K, value: V) -> 'Dict[K, V]':
        """
        Combine keys and values from this dictionary
        with a new dictionary that includes key and value

        :example:
        >>> Dict().set('key', 'value')
        {'key': 'value'}

        :param key: key to add to the new dictionary
        :param value: value to associate with key
        :return: new dictionary with existing keys and values
                 in addition to key and value
        """
        copy = self._d.copy()
        copy[key] = value
        return Dict(copy)

    def without(self, key: K) -> 'Dict[K, V]':
        copy = self._d.copy()
        del copy[key]
        return Dict(copy)

    def get(self, key: K) -> Maybe[V]:
        """
        get the value associated with a key

        :example:
        >>> Dict().get('key', 'default')
        Just('default')
        >>> Dict(key='value').get('key', 'default')
        Just('value')

        :param key: the key to retrieve
        :param default: value to return if the key is not found
        :return: :class:`Just` if key is found in dictionary
                 or default is given,
                 :class:`Nothing` otherwise
        """
        v = self._d.get(key)
        if v is None:
            return Nothing()
        return Just(v)

    def update(self, other: 'Dict[K, V]') -> 'Dict[K, V]':
        d: Dict_[K, V] = {}
        d.update(self._d)
        d.update(other)  # type: ignore
        return Dict(d)
