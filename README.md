## <img src="https://raw.githubusercontent.com/suned/pfun/master/logo/pfun_logo.svg?sanitize=true" style=" width:50px ; height:50px "/> <br> <p align="center">Functional, composable, asynchronous, type-safe Python.</p>

<br>

`pfun` is a Python library that makes functional programming in Python fun and easy. It provides classes and functions that makes working with functional design patterns a breeze, and comes with a [MyPy](http://mypy-lang.org/) plugin that makes static type checking of code written in functional style highly accurate.

<br>

- [Documentation](https://pfun.readthedocs.io/en/latest/)
- [Known issues](https://github.com/suned/pfun/issues?q=is%3Aopen+is%3Aissue+label%3Abug)

## Install

```console
$ pip install pfun
```

Or with optional dependencies:
```console
$ pip install pfun[http,sql]
```

## Resources

### Articles
- [Purely Functional Python With Static Types](https://dev.to/suned/purely-functional-python-with-static-types-41mf)
- [Be More Lazy, Become More Productive](https://dev.to/suned/be-more-lazy-become-more-productive-2cnb)
- [Completely Type-Safe Error Handling in Python](https://dev.to/suned/completely-type-safe-error-handling-in-python-3apg)
- [Completely Type-Safe Dependency Injection in Python](https://dev.to/suned/completely-type-safe-dependency-injection-in-python-48a5)

### Examples
- [Todo-Backend](https://github.com/suned/pfun-todo-backend/) (implementation of [todobackend.com](https://todobackend.com/))
## Support

On [ko-fi](https://ko-fi.com/python_pfun)

## Development

Requires [poetry](https://poetry.eustace.io/)

- Install dependencies with `poetry install`
- Build documentation with `poetry run mkdocs serve`
- Run tests with `poetry run tox`
- Lint with `poetry run pre-commit run --all`
