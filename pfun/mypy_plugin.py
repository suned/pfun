#  type: ignore

import typing as t
from functools import reduce

from mypy import checkmember, infer
from mypy.checker import TypeChecker
from mypy.mro import calculate_mro
from mypy.nodes import ARG_POS, Block, ClassDef, NameExpr, TypeInfo
from mypy.plugin import ClassDefContext, FunctionContext, MethodContext, Plugin
from mypy.plugins.dataclasses import DataclassTransformer
from mypy.types import (ARG_POS, AnyType, CallableType, Instance, Overloaded,
                        Type, TypeVarDef, TypeVarId, TypeVarType, UnionType,
                        get_proper_type)

_CURRY = 'pfun.curry.curry'
_COMPOSE = 'pfun.util.compose'
_IMMUTABLE = 'pfun.immutable.Immutable'
_MAYBE = 'pfun.maybe.maybe'
_MAYBE_WITH_EFFECT = 'pfun.maybe.with_effect'
_LIST_WITH_EFFECT = 'pfun.liste.with_effect'
_EITHER_WITH_EFFECT = 'pfun.either.with_effect'
_READER_WITH_EFFECT = 'pfun.reader.with_effect'
_WRITER_WITH_EFFECT = 'pfun.writer.with_effect'
_STATE_WITH_EFFECT = 'pfun.state.with_effect'
_IO_WITH_EFFECT = 'pfun.io.with_effect'
_TRAMPOLINE_WITH_EFFECT = 'pfun.trampoline.with_effect'
_FREE_WITH_EFFECT = 'pfun.free.with_effect'
_RESULT = 'pfun.result.result'
_IO = 'pfun.io.io'
_READER = 'pfun.reader.reader'
_EITHER = 'pfun.either.either'
_READER_AND_THEN = 'pfun.reader.Reader.and_then'
_EFFECT_COMBINE = 'pfun.effect.combine'
_EITHER_CATCH = 'pfun.either.catch'


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


def _combine_protocols(p1: Instance, p2: Instance) -> Instance:
    def base_repr(base):
        if 'pfun.effect.Intersection' in base.type.fullname:
            return ', '.join([repr(b) for b in base.type.bases])
        return repr(base)

    def get_bases(base):
        if 'pfun.effect.Intersection' in base.type.fullname:
            bases = set()
            for b in base.type.bases:
                bases |= get_bases(b)
            return bases
        return set([base])

    names = p1.type.names.copy()
    names.update(p2.type.names)
    keywords = p1.type.defn.keywords.copy()
    keywords.update(p2.type.defn.keywords)
    bases = get_bases(p1) | get_bases(p2)
    bases_repr = ', '.join(sorted([repr(base) for base in bases]))
    name = f'Intersection[{bases_repr}]'
    defn = ClassDef(
        name,
        Block([]),
        p1.type.defn.type_vars + p2.type.defn.type_vars,
        [NameExpr(p1.type.fullname), NameExpr(p2.type.fullname)],
        None,
        list(keywords.items())
    )
    defn.fullname = f'pfun.effect.{name}'
    info = TypeInfo(names, defn, '')
    info.is_protocol = True
    info.is_abstract = True
    info.bases = [p1, p2]
    info.abstract_attributes = (p1.type.abstract_attributes +
                                p2.type.abstract_attributes)
    calculate_mro(info)
    return Instance(info, p1.args + p2.args)


def _effect_and_then_hook(context: MethodContext) -> Type:
    return_type = context.default_return_type
    return_type_args = return_type.args
    return_type = return_type.copy_modified(args=return_type_args)
    try:
        e1 = context.type
        r1 = e1.args[0]
        e2 = context.arg_types[0][0].ret_type
        r2 = e2.args[0]
        if r1 == r2:
            r3 = r1.copy_modified()
            return_type_args[0] = r3
            return return_type.copy_modified(args=return_type_args)
        elif isinstance(r1, AnyType):
            return_type_args[0] = r2.copy_modified()
            return return_type.copy_modified(args=return_type_args)
        elif isinstance(r2, AnyType):
            return_type_args[0] = r1.copy_modified()
            return return_type.copy_modified(args=return_type_args)
        elif r1.type.is_protocol and r2.type.is_protocol:
            intersection = _combine_protocols(r1, r2)
            return_type_args[0] = intersection
            return return_type.copy_modified(args=return_type_args)
        else:
            return return_type
    except (AttributeError, IndexError):
        return return_type


def _get_environment_hook(context: FunctionContext):
    if context.api.return_types == []:
        return context.default_return_type
    type_context = context.api.return_types[-1]
    if type_context.type.fullname == 'pfun.effect.effect.Effect':
        type_context = get_proper_type(type_context)
        args = context.default_return_type.args
        inferred_r = type_context.args[0]
        args[0] = inferred_r
        args[-1] = inferred_r
        return context.default_return_type.copy_modified(args=args)
    return context.default_return_type


def _combine_hook(context: FunctionContext):
    result_types = []
    error_types = []
    env_types = []
    try:
        for effect_type in context.arg_types[0]:
            env_type, error_type, result_type = effect_type.args
            env_types.append(env_type)
            error_types.append(error_type)
            result_types.append(result_type)
        map_return_type_def = _type_var_def(
            'R1', 'pfun.effect', context.api.named_type('builtins.object')
        )
        map_return_type = TypeVarType(map_return_type_def)
        map_function_type = CallableType(
            arg_types=result_types,
            arg_kinds=[ARG_POS for _ in result_types],
            arg_names=[None for _ in result_types],
            ret_type=map_return_type,
            variables=[map_return_type_def],
            fallback=context.api.named_type('builtins.function')
        )
        ret_type = context.default_return_type.ret_type
        combined_error_type = UnionType(sorted(set(error_types), key=str))
        ret_type_args = ret_type.args
        ret_type_args[1] = combined_error_type
        ret_type_args[2] = map_return_type
        env_types = [
            env_type for env_type in env_types
            if not isinstance(env_type, AnyType)
        ]
        if len(set(env_types)) == 1:
            combined_env_type = env_types[0]
        elif env_types and all(
            hasattr(env_type, 'type') and env_type.type.is_protocol
            for env_type in env_types
        ):
            combined_env_type = reduce(_combine_protocols, env_types)
        else:
            combined_env_type = ret_type_args[0]
        ret_type_args[0] = combined_env_type
        ret_type = ret_type.copy_modified(args=ret_type_args)
        return CallableType(
            arg_types=[map_function_type],
            arg_kinds=[ARG_POS],
            arg_names=[None],
            variables=[map_return_type_def],
            ret_type=ret_type,
            fallback=context.api.named_type('builtins.function')
        )
    except AttributeError:
        return context.default_return_type


def _effect_recover_hook(context: MethodContext) -> Type:
    return_type = context.default_return_type
    return_type_args = return_type.args
    return_type = return_type.copy_modified(args=return_type_args)
    try:
        e1 = context.type
        r1 = e1.args[0]
        e2 = context.arg_types[0][0].ret_type
        r2 = e2.args[0]
        if r1 == r2:
            r3 = r1.copy_modified()
            return_type_args[0] = r3
            return return_type.copy_modified(args=return_type_args)
        elif isinstance(r1, AnyType):
            return_type_args[0] = r2.copy_modified()
            return return_type.copy_modified(args=return_type_args)
        elif isinstance(r2, AnyType):
            return_type_args[0] = r1.copy_modified()
            return return_type.copy_modified(args=return_type_args)
        elif r1.type.is_protocol and r2.type.is_protocol:
            intersection = _combine_protocols(r1, r2)
            return_type_args[0] = intersection
            return return_type.copy_modified(args=return_type_args)
        else:
            return return_type
    except AttributeError:
        return return_type


def _lift_hook(context: FunctionContext) -> Type:
    lifted_arg_types = context.arg_types[0][0].arg_types
    lifted_ret_type = context.arg_types[0][0].ret_type
    return context.default_return_type.copy_modified(
        args=lifted_arg_types + [lifted_ret_type]
    )


def _lift_call_hook(context: MethodContext) -> Type:
    import ipdb
    ipdb.set_trace()
    arg_types = []
    for arg_type in context.arg_types[0]:
        arg_types.append(arg_type.args[-1])
    args = context.type.args[:-1]
    ret_type = context.type.args[-1]
    function_type = CallableType(
        arg_types=args,
        arg_kinds=[ARG_POS] * len(args),
        arg_names=[None] * len(args),
        ret_type=ret_type,
        fallback=context.api.named_type('builtins.function')
    )
    context.api.expr_checker.check_call(callee=function_type, )


class PFun(Plugin):
    def get_function_hook(self, fullname: str
                          ) -> t.Optional[t.Callable[[FunctionContext], Type]]:
        if fullname == _CURRY:
            return _curry_hook
        if fullname == _COMPOSE:
            return _compose_hook
        if fullname in (
            _MAYBE,
            _RESULT,
            _EITHER,
            _IO,
            _READER,
            _MAYBE_WITH_EFFECT,
            _EITHER_WITH_EFFECT,
            _LIST_WITH_EFFECT,
            _READER_WITH_EFFECT,
            _WRITER_WITH_EFFECT,
            _STATE_WITH_EFFECT,
            _IO_WITH_EFFECT,
            _TRAMPOLINE_WITH_EFFECT,
            _FREE_WITH_EFFECT,
            _EITHER_CATCH
        ):
            return _variadic_decorator_hook
        if fullname == 'pfun.effect.effect.get_environment':
            return _get_environment_hook
        if fullname == 'pfun.effect.effect.combine':
            return _combine_hook
        return None

    def get_method_hook(self, fullname: str):
        if fullname == 'pfun.effect.effect.Effect.and_then':
            return _effect_and_then_hook
        if fullname == 'pfun.effect.effect.Effect.recover':
            return _effect_recover_hook

    def get_base_class_hook(self, fullname: str):
        return _immutable_hook


def plugin(_):
    return PFun
