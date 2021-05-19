## <img src="https://raw.githubusercontent.com/suned/pfun/master/logo/pfun_logo.svg?sanitize=true" style=" width:50px ; height:50px "/> <br> <p align="center">Functional, composable, asynchronous, type-safe Python.</p>

- [Documentation](https://pfun.dev)
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
- [How To Make Functional Programming in Python Go Fast](https://dev.to/suned/how-to-make-functional-programming-in-python-go-fast-ad6)

### Examples
- [Todo-Backend](https://github.com/suned/pfun-todo-backend/) (implementation of [todobackend.com](https://todobackend.com/))
## Support

On [ko-fi](https://ko-fi.com/python_pfun)

## Development

Requires [poetry](https://poetry.eustace.io/)

- Install dependencies with `poetry install -E http -E sql`
- Build documentation with `poetry run task serve-docs`
- Run tests with `poetry run task test`
- Lint with `poetry run task lint`
