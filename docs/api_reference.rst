API Reference
=============
pfun
----

.. automodule:: pfun
    :members:
    :imported-members:

pfun.files
-----------------
.. automodule:: pfun.files
    :members:

pfun.console
-------------------
.. automodule:: pfun.console
    :members:

pfun.subprocess
----------------------
.. automodule:: pfun.subprocess
    :members:

pfun.logging
-------------------
.. automodule:: pfun.logging
    :members:

pfun.ref
---------------
.. automodule:: pfun.ref
    :members:

pfun.http
----------------
.. note::
    This module requires optional dependencies. You can install them together
    with ``pfun`` using ``pip install pfun[http]``.

.. automodule:: pfun.http
    :members:

pfun.sql
----------------
.. note::
    This module requires optional dependencies. You can install them together
    with ``pfun`` using ``pip install pfun[sql]``.

.. note::
    ``pfun.sql`` currently only supports Postgres databases

.. automodule:: pfun.sql
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
