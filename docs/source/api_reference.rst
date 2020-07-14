API Reference
=============
pfun
----

.. autoclass:: pfun.Immutable
    :members:



.. autoclass:: pfun.Dict
    :members:
    :special-members:
    :exclude-members: __weakref__,clear,__setitem__,__delitem__

.. autoclass:: pfun.List
    :members:
    :special-members:
    :exclude-members: __weakref__,clear,__setitem__,__delitem__


.. autofunction:: pfun.curry


.. autofunction:: pfun.compose


.. autofunction:: pfun.always


.. autofunction:: pfun.pipeline


.. autofunction:: pfun.identity


pfun.effect
-----------
.. automodule:: pfun.effect
    :members:
    :imported-members:

pfun.effect.files
-----------------
.. automodule:: pfun.effect.files
    :members:

pfun.effect.console
-------------------
.. automodule:: pfun.effect.console
    :members:

pfun.effect.subprocess
----------------------
.. automodule:: pfun.effect.subprocess
    :members:

pfun.effect.logging
-------------------
.. automodule:: pfun.effect.logging
    :members:

pfun.effect.ref
---------------
.. automodule:: pfun.effect.ref
    :members:

pfun.effect.http
----------------
.. note::
    This module requires optional dependencies. You can install them together
    with ``pfun`` using ``pip install pfun[http]``.

.. automodule:: pfun.effect.http
    :members:

pfun.effect.sql
----------------
.. note::
    This module requires optional dependencies. You can install them together
    with ``pfun`` using ``pip install pfun[sql]``.

.. note::
    ``pfun.effect.sql`` currently only supports Postgres databases

.. automodule:: pfun.effect.sql
    :members:

pfun.maybe
----------
.. autofunction:: pfun.maybe.maybe

.. autoattribute:: pfun.maybe.Maybe

.. autoclass:: pfun.maybe.Just
    :members:

.. autoclass:: pfun.maybe.Nothing
    :members:

pfun.either
-----------
.. autofunction:: pfun.either.either


.. autoattribute:: pfun.either.Either

.. autoclass:: pfun.result.Right
    :members:

.. autoclass:: pfun.result.Left
    :members:

pfun.trampoline
---------------

.. automodule:: pfun.trampoline
    :members:
    :special-members:
    :exclude-members: __weakref__,__setattr__,__repr__
