def build(setup_kwargs):
    setup_kwargs.update(
        {
            "package_data": {"pfun": ["py.typed"]}
        }
    )
