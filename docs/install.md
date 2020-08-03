## From PyPI

`pfun` can be installed from [PyPI](https://pypi.org/project/pfun/), for example using `pip`:

```console
$ pip install pfun
```

Some modules such as `pfun.sql` and `pfun.http` require optional dependencies. These can be installed with:

```console
$ pip install pfun[sql,http]
```

## MyPy Plugin

The types provided by the Python `typing` module are often not flexible enough to provide
precise typing of common functional design patterns. If you use [mypy](http://mypy-lang.org/), `pfun`
provides a plugin that enables more precise types which can identify more bugs caused by
type errors. To enable the `pfun` mypy plugin,
add the following to your mypy configuration:
```
[mypy]
plugins = pfun.mypy_plugin
```
