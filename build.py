from setuptools.extension import Extension


def build(setup_kwargs):
    extensions = [Extension("pfun.effect", ['src/pfun/effect.c'])]
    setup_kwargs.update(
        {
            "ext_modules": extensions
        }
    )
