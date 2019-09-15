#  type: ignore

import typing as t

from mypy.plugin import Plugin, FunctionContext, ClassDefContext
from mypy.plugins.dataclasses import DataclassTransformer
from mypy.types import (
    Type,
    CallableType,
    Instance,
    TypeVarType,
    Overloaded,
    TypeVarId,
    TypeVarDef
)
from mypy.nodes import ClassDef, ARG_POS
from mypy import checkmember, infer
from mypy.checker import TypeChecker

_CURRY = 'pfun.curry.curry'
_COMPOSE = 'pfun.util.compose'
_IMMUTABLE = 'pfun.immutable.Immutable'
_MAYBE = 'pfun.maybe.maybe'
_RESULT = 'pfun.result.result'
_IO = 'pfun.io.io'
_READER = 'pfun.reader.reader'
_EITHER = 'pfun.either.either'
_READER_AND_THEN = 'pfun.reader.Reader.and_then'


def _get_callable_type(type_: Type,
                       context: FunctionContext) -> t.Optional[CallableType]:
    if isinstance(type_, CallableType):
        return type_
        # called with an object
    elif isinstance(type_, Instance) and type_.has_readable_member('__call__'):
        chk: TypeChecker = t.cast(TypeChecker, context.api)
        return t.cast(
            CallableType,
            checkmember.analyze_member_access(
                '__call__',
                type_,
                context.context,
                False,
                False,
                False,
                context.api.msg,
                original_type=type_,
                chk=chk
            )
        )
    return None


def _curry_hook(context: FunctionContext) -> Type:
    arg_type = context.arg_types[0][0]
    function = _get_callable_type(arg_type, context)
    if function is None:
        return context.default_return_type

    if not function.arg_types:
        return function
    return_type = function.ret_type
    last_function = CallableType(
        arg_types=[function.arg_types[-1]],
        arg_kinds=[function.arg_kinds[-1]],
        arg_names=[function.arg_names[-1]],
        ret_type=return_type,
        fallback=function.fallback
    )
    args = list(
        zip(
            function.arg_types[:-1],
            function.arg_kinds[:-1],
            function.arg_names[:-1]
        )
    )
    for arg_type, kind, name in reversed(args):
        last_function = CallableType(
            arg_types=[arg_type],
            arg_kinds=[kind],
            arg_names=[name],
            ret_type=last_function,
            fallback=function.fallback,
            variables=function.variables,
            implicit=True
        )
    return Overloaded([last_function, function])


def _variadic_decorator_hook(context: FunctionContext) -> Type:
    arg_type = context.arg_types[0][0]
    function = _get_callable_type(arg_type, context)
    if function is None:
        return context.default_return_type

    ret_type = context.default_return_type.ret_type
    variables = list(
        set(function.variables + context.default_return_type.variables)
    )
    return CallableType(
        arg_types=function.arg_types,
        arg_kinds=function.arg_kinds,
        arg_names=function.arg_names,
        ret_type=ret_type,
        fallback=function.fallback,
        variables=variables,
        implicit=True
    )


def _type_var_def(
    name: str, module: str, upper_bound, values=(), meta_level=0
) -> TypeVarDef:
    id_ = TypeVarId.new(meta_level)
    id_.raw_id = -id_.raw_id
    fullname = f'{module}.{name}'
    return TypeVarDef(name, fullname, id_, list(values), upper_bound)


def _get_compose_type(context: FunctionContext) -> t.Optional[CallableType]:
    # TODO, why are the arguments lists of lists,
    # and do I need to worry about it?
    n_args = len([at for ats in context.arg_types for at in ats])

    arg_types = []
    arg_kinds = []
    arg_names = []
    ret_type_def = _type_var_def(
        'R1', 'pfun.compose', context.api.named_type('builtins.object')
    )
    ret_type = TypeVarType(ret_type_def)
    variables = [ret_type_def]
    for n in range(n_args):
        current_arg_type_def = _type_var_def(
            f'R{n + 2}',
            'pfun.compose',
            context.api.named_type('builtins.object')
        )
        current_arg_type = TypeVarType(current_arg_type_def)
        arg_type = CallableType(
            arg_types=[current_arg_type],
            ret_type=ret_type,
            arg_kinds=[ARG_POS],
            arg_names=[None],
            variables=[current_arg_type_def, ret_type_def],
            fallback=context.api.named_type('builtins.function')
        )
        arg_types.append(arg_type)
        arg_kinds.append(ARG_POS)
        arg_names.append(None)
        variables.append(current_arg_type_def)
        ret_type_def = current_arg_type_def
        ret_type = current_arg_type
    first_arg_type, *_, last_arg_type = arg_types
    ret_type = CallableType(
        arg_types=last_arg_type.arg_types,
        arg_names=last_arg_type.arg_names,
        arg_kinds=last_arg_type.arg_kinds,
        ret_type=first_arg_type.ret_type,
        variables=[first_arg_type.variables[-1], last_arg_type.variables[0]],
        fallback=context.api.named_type('builtins.function')
    )
    return CallableType(
        arg_types=arg_types,
        arg_kinds=arg_kinds,
        arg_names=arg_names,
        ret_type=ret_type,
        variables=variables,
        fallback=context.api.named_type('builtins.function'),
        name='compose'
    )


def _compose_hook(context: FunctionContext) -> Type:
    compose = _get_compose_type(context)
    inferred = infer.infer_function_type_arguments(
        compose, [arg for args in context.arg_types for arg in args],
        [kind for kinds in context.arg_kinds for kind in kinds],
        [
            [i, i] for i in
            range(len([arg for args in context.arg_types for arg in args]))
        ]
    )
    ret_type = context.api.expr_checker.apply_inferred_arguments(
        compose, inferred, context.context
    ).ret_type
    ret_type.variables = []
    return ret_type


def _immutable_hook(context: ClassDefContext):
    cls: ClassDef = context.cls
    if not cls.info.has_base(_IMMUTABLE):
        return
    transformer = DataclassTransformer(context)
    transformer.transform()
    attributes = transformer.collect_attributes()
    transformer._freeze(attributes)


def _and_then_hook(context: FunctionContext) -> Type:

    return context.default_return_type


class PFun(Plugin):
    def get_function_hook(self, fullname: str
                          ) -> t.Optional[t.Callable[[FunctionContext], Type]]:
        if fullname == _CURRY:
            return _curry_hook
        if fullname == _COMPOSE:
            return _compose_hook
        if fullname == _MAYBE:
            return _variadic_decorator_hook
        if fullname == _RESULT:
            return _variadic_decorator_hook
        if fullname == _EITHER:
            return _variadic_decorator_hook
        if fullname == _IO:
            return _variadic_decorator_hook
        if fullname == _READER:
            return _variadic_decorator_hook

    def get_method_hook(self, fullname: str):
        if fullname == _READER_AND_THEN:
            return _and_then_hook
        return None

    def get_base_class_hook(self, fullname: str):
        return _immutable_hook


def plugin(_):
    return PFun
