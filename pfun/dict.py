from typing import Dict as Dict_
from typing import (ItemsView, Iterator, KeysView, Mapping, TypeVar, Union,
                    ValuesView)

from .immutable import Immutable
from .maybe import Just, Maybe, Nothing

K = TypeVar('K')
V = TypeVar('V')


class Dict(Immutable, Mapping[K, V], init=False):
    """
    Immutable dictionary class with functional helper methods
    """

    _d: Dict_[K, V]

    def __init__(self, d: Union[Dict_[K, V], 'Dict[K, V]'] = dict()):
        """
        Args:
            d: `dict` instance to wrap
        """
        if isinstance(d, Dict):
            d = d._d
        object.__setattr__(self, '_d', dict(d))

    def __repr__(self):
        return f'Dict({repr(self._d)})'

    def __eq__(self, other) -> bool:
        """
        Compare `self` with `other`

        Return:
            `True` if keys and associated values \
            are equal, `False` otherwise
        """
        if isinstance(other, dict):
            return other == self._d
        if isinstance(other, Dict):
            return other._d == self._d
        return False

    def keys(self) -> KeysView[K]:
        """
        Get the keys in this dictionary

        Example:
            >>> Dict({'key': 'value'}).keys()
            dict_keys(['key'])

        Return:
            Dictionary keys
        """
        return self._d.keys()

    def values(self) -> ValuesView[V]:
        """
        Get the values in this dictionary

        Example:
            >>> Dict({'key': 'value'}).values()
            dict_values(['value'])

        Return:
            Dictionary values
        """
        return self._d.values()

    def copy(self) -> 'Dict[K, V]':
        """
        Get a shallow copy of this dictionary.

        Example:
            >>> Dict({'key': 'value'}).copy()
            Dict({'key': 'value'})

        Return:
            Copy of this dict
        """
        return Dict(self._d.copy())

    def items(self) -> ItemsView[K, V]:
        """
        Get the keys and values of this dictionary

        Example:
            >>> Dict({'key': 'value'}).items()
            dict_items([('key', 'value')])

        Return:
            Keys and values of this dictionary
        """
        return self._d.items()

    def __contains__(self, key: object) -> bool:
        """
        Test if ``key`` is a key in this dictionary

        Example:
            >>> 'key' in Dict({'key': 'value'})
            True

        Args:
            key: The key to test for membership
        Return:
            ``True`` if ``key`` is a key in this dictionary,
                 ``False`` otherwise
        """
        return key in self._d

    def __getitem__(self, key: K) -> V:
        """
        get the value associated with a key

        Example:
            >>> Dict(key='value')['key']
            'value'
        Args:
            key: the key to retrieve
            Return:
            value associated with key
        """
        return self._d[key]

    def __iter__(self) -> Iterator[K]:
        """
        Get an iterator over the keys in this dictionary

        Example:
            >>> tuple(Dict({'key': 'value'}))
            ('key',)

        Return:
            Iterator of the keys in this dictionary
        """
        return iter(self._d)

    def __len__(self) -> int:
        """
        Get the number of key/value pairs in this dictionary

        Example:
            >>> len(Dict({'key': 'value'}))
            1

        Return:
            Number of key/value pairs in this dictionary
        """
        return len(self._d)

    def set(self, key: K, value: V) -> 'Dict[K, V]':
        """
        Combine keys and values from this dictionary
        with a new dictionary that includes key and value

        Example:
            >>> Dict().set('key', 'value')
            {'key': 'value'}

        Args:
            key: key to add to the new dictionary
            value: value to associate with key
        Return:
            new dictionary with existing keys and values
                 in addition to key and value
        """
        copy = self._d.copy()
        copy[key] = value
        return Dict(copy)

    def without(self, key: K) -> 'Dict[K, V]':
        """
        Get a copy of this dictionary without
        the mapping associated with ``key``.

        Example:
            >>> Dict({'key': 'value'}).without('key')
            Dict({})

        Args:
            key: The ``key`` to remove
        Return:
            Copy of this dictionary without ``key``
        """
        copy = self._d.copy()
        try:
            del copy[key]
        except KeyError:
            pass
        return Dict(copy)

    def get(self, key: K) -> Maybe[V]:  # type: ignore
        """
        get the value associated with a key

        Example:
            >>> Dict().get('key')
            Nothing()
            >> Dict({'key': 'value'}).get('key')
            Just('value')

        Args:
            key: the key to retrieve
            default: value to return if the key is not found
        Return:
            `Just` if key is found in dictionary
                 or default is given,
                 `Nothing` otherwise
        """
        v = self._d.get(key)
        if v is None:
            return Nothing()
        return Just(v)

    def update(
        self, other: Union[Mapping[K, V], 'Dict[K, V]']
    ) -> 'Dict[K, V]':
        """
        Get a copy of this dictionary updated with key/value pairs
        from ``other``

        Example:
            >>> Dict({'key': 'value'}).update({'new_key': 'new_value'})
            Dict({'key': 'value', 'new_key': 'new_value'})
        Args:
            other: Dict to add to keys/values of this dictionary
        Return:
            copy of `self` with keys and values added
        """
        d: Dict_[K, V] = {}
        d.update(self._d)
        d.update(other)
        return Dict(d)


__all__ = ['Dict']
