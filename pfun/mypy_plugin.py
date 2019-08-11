import typing as t

from mypy.plugin import Plugin, FunctionContext, ClassDefContext
from mypy.plugins.dataclasses import DataclassTransformer
from mypy.types import Type, CallableType, AnyType, TypeOfAny, Instance
from mypy.nodes import ClassDef
from mypy import checkmember

_CURRY = 'pfun.curry.curry'
_COMPOSE = 'pfun.util.compose'
_IMMUTABLE = 'pfun.immutable.Immutable'


def _curry_hook(context: FunctionContext) -> Type:
    arg_type = context.arg_types[0][0]
    if not isinstance(arg_type, CallableType):
        # called with an object
        if isinstance(arg_type, Instance) and arg_type.has_readable_member('__call__'):
            function = checkmember.analyze_member_access(
                '__call__',
                arg_type,
                context.context,
                False,
                False,
                False,
                context.api.msg,
                original_type=arg_type,
                chk=context.api
            )
        else:
            # called with an object without __call__ member: defer to normal type check
            return context.default_return_type
    else:
        function = arg_type

    if not isinstance(function, CallableType):
        return context.default_return_type
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


def _get_expected_compose_type(context: FunctionContext) -> CallableType:
    # TODO, why are the arguments lists of lists, and do I need to worry about it?
    actual_arg_types = [at for ats in context.arg_types for at in ats]
    actual_arg_kinds = [ak for aks in context.arg_kinds for ak in aks]
    actual_arg_names = [an for ans in context.arg_names for an in ans]
    arg_types = []
    arg_kinds = []
    arg_names = []
    args = list(
        zip(actual_arg_types,
            actual_arg_kinds,
            actual_arg_names)
    )
    for index, (arg_type, arg_kind, arg_name) in enumerate(args):
        is_last_arg = index == len(actual_arg_types) - 1
        is_first_arg = index == 0
        if is_last_arg:
            # if this is the last function,
            # the arguments are just the arguments to the function
            current_arg_types = arg_type.arg_types
            current_arg_kinds = arg_type.arg_kinds
            current_arg_names = arg_type.arg_names
        else:
            # otherwise, the arguments must be the return type of the next function
            current_arg_types = [actual_arg_types[index + 1].ret_type]
            current_arg_kinds = [arg_type.arg_kinds[0]]
            current_arg_names = [arg_type.arg_names[0]]

        if is_first_arg:
            # if this is the first function,
            # the return type can by anything
            ret_type = AnyType(TypeOfAny.explicit)
        else:
            # otherwise, the return type must be the argument of the previous function
            ret_type = actual_arg_types[index - 1].arg_types[0]

        arg_types.append(
            CallableType(
                arg_types=current_arg_types,
                arg_names=current_arg_names,
                arg_kinds=current_arg_kinds,
                ret_type=ret_type,
                fallback=arg_type.fallback
            )
        )
        arg_kinds.append(arg_kind)
        arg_names.append(arg_name)
    first_arg_type, *_, last_arg_type = actual_arg_types
    ret_type = CallableType(
        arg_types=last_arg_type.arg_types,
        arg_names=last_arg_type.arg_names,
        arg_kinds=last_arg_type.arg_kinds,
        ret_type=first_arg_type.ret_type,
        fallback=context.api.named_type('builtins.function')
    )
    return CallableType(
        arg_types=arg_types,
        arg_kinds=arg_kinds,
        arg_names=arg_names,
        ret_type=ret_type,
        fallback=context.api.named_type('builtins.function'),
        name='compose'
    )


def _compose_hook(context: FunctionContext) -> Type:
    api = context.api
    try:
        compose = _get_expected_compose_type(context)
        api.expr_checker.check_call(
            compose,
            [arg for args in context.args for arg in args],
            [kind for kinds in context.arg_kinds for kind in kinds],
            context.context,
            [name for names in context.arg_names for name in names]
        )
        return compose.ret_type
    except AttributeError:
        # an argument was not callable, defer to default type checking
        return context.default_return_type


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
        if fullname == _COMPOSE:
            return _compose_hook
        return None

    def get_base_class_hook(self, fullname: str):
        return _immutable_hook


def plugin(_):
    return PFun
