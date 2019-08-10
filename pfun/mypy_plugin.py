import typing as t

import mypy
from mypy.plugin import Plugin, FunctionContext, ClassDefContext
from mypy.plugins.dataclasses import DataclassTransformer
from mypy.types import Type, CallableType
from mypy.nodes import ClassDef

_CURRY = 'pfun.curry.curry'
_IMMUTABLE = 'pfun.immutable.Immutable'


def _curry_hook(context: FunctionContext) -> Type:
    function = t.cast(CallableType, context.arg_types[0][0])
    if not function.arg_names:
        return function
    return_type = function.ret_type
    last_function = CallableType(
        arg_types=[function.arg_types[-1]],
        arg_kinds=[function.arg_kinds[-1]],
        arg_names=[function.arg_names[-1]],
        ret_type=return_type,
        fallback=function.fallback
    )
    args = list(zip(
        function.arg_types[:-1],
        function.arg_kinds[:-1],
        function.arg_names[:-1]
    ))
    for arg_type, kind, name in reversed(args):
        last_function = CallableType(
            arg_types=[arg_type],
            arg_kinds=[kind],
            arg_names=[name],
            ret_type=last_function,
            fallback=function.fallback
        )
    return last_function


def _immutable_hook(context: ClassDefContext):
    cls: ClassDef = context.cls
    if not cls.info.has_base(_IMMUTABLE):
        return
    transformer = DataclassTransformer(context)
    transformer.transform()
    attributes = transformer.collect_attributes()
    transformer._freeze(attributes)


class PFun(Plugin):
    def get_function_hook(self,
                          fullname: str
                          ) -> t.Optional[t.Callable[[FunctionContext], Type]]:
        if fullname == _CURRY:
            return _curry_hook
        return None

    def get_base_class_hook(self, fullname: str):
        return _immutable_hook


def plugin(_):
    return PFun
