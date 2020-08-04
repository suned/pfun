#  type: ignore

import typing as t
from functools import reduce

from mypy import checkmember, infer
from mypy.checker import TypeChecker
from mypy.mro import calculate_mro
from mypy.nodes import ARG_POS, Block, ClassDef, NameExpr, TypeInfo
from mypy.plugin import (ClassDefContext, FunctionContext, MethodContext,
                         MethodSigContext, Plugin)
from mypy.plugins.dataclasses import DataclassTransformer
from mypy.types import (ARG_POS, AnyType, CallableType, Instance, Overloaded,
                        Type, TypeOfAny, TypeVarDef, TypeVarId, TypeVarType,
                        UnionType, get_proper_type)

_CURRY = 'pfun.functions.curry'
_COMPOSE = 'pfun.functions.compose'
_IMMUTABLE = 'pfun.immutable.Immutable'
_MAYBE = 'pfun.maybe.maybe'
_RESULT = 'pfun.result.result'
_EITHER = 'pfun.either.either'
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

    ret_type = get_proper_type(context.default_return_type.ret_type)
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
        if 'pfun.Intersection' in base.type.fullname:
            return ', '.join([repr(b) for b in base.type.bases])
        return repr(base)

    def get_bases(base):
        if 'pfun.Intersection' in base.type.fullname:
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
    defn.fullname = f'pfun.{name}'
    info = TypeInfo(names, defn, '')
    info.is_protocol = True
    info.is_abstract = True
    info.bases = [p1, p2]
    info.abstract_attributes = (
        p1.type.abstract_attributes + p2.type.abstract_attributes
    )
    calculate_mro(info)
    return Instance(info, p1.args + p2.args)


def _combine_environments(r1: Type, r2: Type) -> Type:
    if r1 == r2:
        return r1.copy_modified()
    elif isinstance(r1, Instance) and r1.type.fullname == 'builtins.object':
        return r2.copy_modified()
    elif isinstance(r2, Instance) and r2.type.fullname == 'builtins.object':
        return r1.copy_modified()
    elif r1.type.is_protocol and r2.type.is_protocol:
        return _combine_protocols(r1, r2)
    else:
        return AnyType(TypeOfAny.special_form)


def _effect_and_then_hook(context: MethodContext) -> Type:
    return_type = context.default_return_type
    return_type_args = return_type.args
    return_type = return_type.copy_modified(args=return_type_args)
    try:
        e1 = get_proper_type(context.type)
        r1 = e1.args[0]
        e2 = get_proper_type(context.arg_types[0][0].ret_type)
        r2 = e2.args[0]
        return_type_args[0] = _combine_environments(r1, r2)
        return return_type.copy_modified(args=return_type_args)
    except (AttributeError, IndexError):
        return return_type


def _combine_hook(context: FunctionContext):
    result_types = []
    error_types = []
    env_types = []
    try:
        for effect_type in context.arg_types[0]:
            env_type, error_type, result_type = get_proper_type(
                effect_type
            ).args
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
        combined_error_type = UnionType.make_union(
            sorted(set(error_types), key=str)
        )
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
    try:
        e1 = get_proper_type(context.type)
        r1 = e1.args[0]
        e2 = get_proper_type(context.arg_types[0][0].ret_type)
        r2 = e2.args[0]
        return_type_args[0] = _combine_environments(r1, r2)
        return return_type.copy_modified(args=return_type_args)
    except AttributeError:
        return return_type


def _lift_hook(context: FunctionContext) -> Type:
    lifted_arg_types = context.arg_types[0][0].arg_types
    lifted_ret_type = context.arg_types[0][0].ret_type
    return context.default_return_type.copy_modified(
        args=lifted_arg_types + [lifted_ret_type]
    )


def _lift_call_hook(context: MethodContext) -> Type:
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


def _effect_catch_hook(context: FunctionContext) -> Type:
    error_types = [
        arg_type[0].ret_type for arg_type in context.arg_types if arg_type
    ]
    return context.default_return_type.copy_modified(args=error_types)


def _effect_catch_call_hook(context: MethodContext) -> Type:
    f_type = _get_callable_type(context.arg_types[0][0], context)
    if len(context.type.args) == 1:
        return context.default_return_type.copy_modified(
            arg_types=f_type.arg_types,
            arg_kinds=f_type.arg_kinds,
            arg_names=f_type.arg_names
        )
    args = context.type.args
    error_union = UnionType.make_union(args)
    effect_type = get_proper_type(context.default_return_type.ret_type)
    r, e, a = effect_type.args
    effect_type = effect_type.copy_modified(args=[r, error_union, a])

    return context.default_return_type.copy_modified(
        ret_type=effect_type,
        arg_types=f_type.arg_types,
        arg_kinds=f_type.arg_kinds,
        arg_names=f_type.arg_names
    )


def _effect_discard_and_then_hook(context: MethodContext) -> Type:
    return_type = context.default_return_type
    return_type_args = return_type.args
    return_type = return_type.copy_modified(args=return_type_args)
    try:
        e1 = get_proper_type(context.type)
        r1 = e1.args[0]
        e2 = get_proper_type(context.arg_types[0][0])
        r2 = e2.args[0]
        return_type_args[0] = _combine_environments(r1, r2)
        return return_type.copy_modified(args=return_type_args)
    except TypeError:
        return return_type


def _effect_ensure_hook(context: MethodContext) -> Type:
    return_type = context.default_return_type
    return_type_args = return_type.args
    return_type = return_type.copy_modified(args=return_type_args)
    try:
        e1 = get_proper_type(context.type)
        r1 = e1.args[0]
        e2 = get_proper_type(context.arg_types[0][0])
        r2 = e2.args[0]
        return_type_args[0] = _combine_environments(r1, r2)
        return return_type.copy_modified(args=return_type_args)
    except TypeError:
        return return_type


def _effect_lift_call_hook(context: MethodContext) -> Type:
    try:
        f = context.type.args[0]
        if isinstance(f, AnyType):
            return context.default_return_type
        as_ = []
        rs = []
        es = []
        for effect_type in context.arg_types:
            r, e, a = get_proper_type(effect_type[0]).args
            as_.append(a)
            rs.append(r)
            es.append(e)
        inferred = infer.infer_function_type_arguments(
            f,
            as_, [kind for kinds in context.arg_kinds for kind in kinds],
            [[i, i] for i in range(len(as_))]
        )
        a = context.api.expr_checker.apply_inferred_arguments(
            f, inferred, context.context
        ).ret_type
        r = reduce(_combine_environments, rs)
        e = UnionType.make_union(sorted(set(es), key=str))
        return context.default_return_type.copy_modified(args=[r, e, a])
    except AttributeError:
        return context.default_return_type


def _effect_lift_call_signature_hook(context: MethodSigContext):
    try:
        f = context.type.args[0]
        f_arg_types = f.arg_types
        default_effect = get_proper_type(
            context.default_signature.arg_types[0]
        )
        r, e, a = default_effect.args
        arg_types = []
        for arg_type in f_arg_types:
            arg_types.append(
                default_effect.copy_modified(args=[r, e, arg_type])
            )
        return context.default_signature.copy_modified(
            arg_types=arg_types,
            arg_names=f.arg_names,
            arg_kinds=f.arg_kinds,
            variables=f.variables
        )
    except AttributeError:
        return context.default_signature


def _effect_cpu_bound_hook(context: FunctionContext) -> Type:
    try:
        f_type = context.arg_types[0][0]
        if f_type.ret_type.type.fullname == 'typing.Coroutine':
            context.api.fail(
                "Function arguments to 'pfun.effect.cpu_bound' can't be async",
                context.context
            )
        return context.default_return_type
    except AttributeError:
        return context.default_return_type


def _effect_io_bound_hook(context: FunctionContext) -> Type:
    try:
        f_type = context.arg_types[0][0]
        if f_type.ret_type.type.fullname == 'typing.Coroutine':
            context.api.fail(
                "Function arguments to 'pfun.effect.io_bound' can't be async",
                context.context
            )
        return context.default_return_type
    except AttributeError:
        return context.default_return_type


class PFun(Plugin):
    def get_function_hook(self, fullname: str
                          ) -> t.Optional[t.Callable[[FunctionContext], Type]]:
        if fullname == 'pfun.effect.catch':
            return _effect_catch_hook
        if fullname == _CURRY:
            return _curry_hook
        if fullname == _COMPOSE:
            return _compose_hook
        if fullname in (
            _MAYBE, _RESULT, _EITHER, _EITHER_CATCH, 'pfun.effect.catch_all'
        ):
            return _variadic_decorator_hook
        if fullname == 'pfun.effect.combine':
            return _combine_hook
        if fullname == 'pfun.effect.cpu_bound':
            return _effect_cpu_bound_hook
        if fullname == 'pfun.effect.io_bound':
            return _effect_io_bound_hook
        return None

    def get_method_hook(self, fullname: str):
        if fullname == 'pfun.effect.Effect.and_then':
            return _effect_and_then_hook
        if fullname == 'pfun.effect.Effect.discard_and_then':
            return _effect_discard_and_then_hook
        if fullname == 'pfun.effect.Effect.ensure':
            return _effect_ensure_hook
        if fullname == 'pfun.effect.Effect.recover':
            return _effect_recover_hook
        if fullname == 'pfun.effect.catch.__call__':
            return _effect_catch_call_hook
        if fullname == 'pfun.effect.lift.__call__':
            return _effect_lift_call_hook

    def get_method_signature_hook(self, fullname: str):
        if fullname == 'pfun.effect.lift.__call__':
            return _effect_lift_call_signature_hook

    def get_base_class_hook(self, fullname: str):
        return _immutable_hook


def plugin(_):
    return PFun
