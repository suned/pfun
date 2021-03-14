from Cython.Build import cythonize


def build(setup_kwargs):
    setup_kwargs.update(
        {
            "package_data": {"pfun": ["py.typed"]},
            "ext_modules": cythonize(["pfun/effect.pyx"])
        }
    )
