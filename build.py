from setuptools.extension import Extension
import os


def build(setup_kwargs):
    os.system("cythonize src/pfun/effect.pyx")
    extensions = [Extension("pfun.effect", ['src/pfun/effect.c'])]
    setup_kwargs.update(
        {
            "ext_modules": extensions
        }
    )

if __name__ == '__main__':
    build({})