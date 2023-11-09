from setuptools.extension import Extension
from Cython.Build import cythonize


def build(setup_kwargs):
    cythonize("src/pfun/effect.pyx")
    extensions = [
        Extension("pfun.effect", ['src/pfun/effect.c']),
    ]
    setup_kwargs.update(
        {
            "ext_modules": extensions
        }
    )
