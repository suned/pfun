from setuptools.extension import Extension


def build(setup_kwargs):
    try:
        from Cython.Build import cythonize
        extensions = cythonize(['pfun/effect.pyx'])
    except ImportError:
        extensions = [Extension("pfun.effect", ['pfun/effect.c'])]
    setup_kwargs.update(
        {
            "ext_modules": extensions
        }
    )
