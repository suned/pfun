#  type: ignore
import typing as t
from functools import reduce

from mypy import checkmember, infer
from mypy.argmap import map_actuals_to_formals, map_formals_to_actuals
from mypy.checker import TypeChecker
from mypy.checkmember import analyze_member_access
from mypy.expandtype import freshen_function_type_vars, expand_type
from mypy.mro import calculate_mro
from mypy.nodes import (ARG_NAMED_OPT, ARG_OPT, ARG_POS, ARG_STAR, ARG_STAR2,
                        MDEF, Argument, Block, CallExpr, ClassDef, Expression,
                        FakeInfo, FuncDef, NameExpr, OpExpr, PassStmt,
                        Statement, SymbolTable, SymbolTableNode, TypeInfo, Var, INVARIANT, COVARIANT)
from mypy.plugin import (AttributeContext, ClassDefContext, FunctionContext,
                         MethodContext, MethodSigContext, Plugin)
from mypy.plugins.dataclasses import DataclassTransformer
from mypy.semanal import set_callable_name
from mypy.types import (AnyType, CallableType, Instance, Overloaded, Type,
                        TypeOfAny, TypeVarDef, TypeVarId, TypeVarType,
                        UnionType, get_proper_type, UninhabitedType, TupleType)
from mypy.typevars import fill_typevars
from mypy.typeops import bind_self, get_type_vars
from mypy.checkexpr import has_uninhabited_component
from mypy.stats import is_complex
from mypy.type_visitor import TypeTranslator

from .functions import curry

_COMPOSE = 'pfun.functions.compose'
_IMMUTABLE = 'pfun.immutable.Immutable'
_MAYBE = 'pfun.maybe.maybe'
_RESULT = 'pfun.result.result'
_EITHER = 'pfun.either.either'
_EFFECT_COMBINE = 'pfun.effect.combine'
_EITHER_CATCH = 'pfun.either.catch'


class ReplaceTypeVar(TypeTranslator):
    """
    Visitor that replaces a target type variable and defintion with
    new 
    """
    def __init__(self, 
                 target_t_var: TypeVarType,
                 replacement_t_var: TypeVarType,
                 target_t_def: t.Optional[TypeVarDef] = None,
                 replacement_t_def: t.Optional[TypeVarDef] = None):
        self.target_t_var = target_t_var
        self.target_t_def = target_t_def
        self.replacement_t_var = replacement_t_var
        self.replacement_t_def = replacement_t_def

    def translate_variables(self, variables):
        return [v if v != self.target_t_def else self.replacement_t_def for v in variables]
    
    def visit_type_var(self, t: TypeVarType):
        return t if t != self.target_t_var else self.replacement_t_var


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
    name: str, module: str, upper_bound, values=(), meta_level=0, variance=INVARIANT
) -> TypeVarDef:
    id_ = TypeVarId.new(meta_level)
    id_.raw_id = -id_.raw_id
    fullname = f'{module}.{name}'
    return TypeVarDef(name, fullname, id_, list(values), upper_bound, variance)


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


def _create_protocol_type(
    name: str,
    base_types: t.List[Expression] = None,
    type_vars: t.List[TypeVarDef] = None,
    args=(),
    body: t.List[Statement] = (),
    names: SymbolTable = None,
    abstract_attributes: t.List[str] = ()
):
    defn = ClassDef(name, Block(list(body)), type_vars, base_types, None, [])
    defn.fullname = f'pfun.{name}'
    info = TypeInfo(names, defn, '')
    info.bases = base_types
    info.is_protocol = True
    info.is_abstract = True
    info.abstract_attributes = list(abstract_attributes)
    calculate_mro(info)
    for node in names.values():
        node.node.info = info
    instance = Instance(info, args)
    return defn, info, instance


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
    return_type_args = list(return_type.args)
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
        ret_type_args = list(ret_type.args)
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
    return_type_args = list(return_type.args)
    try:
        e1 = get_proper_type(context.type)
        r1 = e1.args[0]
        e2 = get_proper_type(context.arg_types[0][0].ret_type)
        r2 = e2.args[0]
        return_type_args[0] = _combine_environments(r1, r2)
        return return_type.copy_modified(args=return_type_args)
    except (AttributeError, IndexError):
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
    try:
        error_types = [
            arg_type[0].ret_type for arg_type in context.arg_types if arg_type
        ]
        return context.default_return_type.copy_modified(args=error_types)
    except AttributeError:
        return context.default_return_type


def _effect_catch_call_hook(context: MethodContext) -> Type:
    f_type = _get_callable_type(context.arg_types[0][0], context)
    if f_type is None:
        return context.default_return_type
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
    return_type_args = list(return_type.args)
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
    return_type_args = list(return_type.args)
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


@curry
def _lens_getattr_hook(fullname: str, context: AttributeContext) -> Type:
    attr_name = fullname.split('.')[-1]
    t = context.type.args[-1]
    if isinstance(t, AnyType):
        return context.default_attr_type
    if context.api.expr_checker.has_member(t, attr_name):
        attr_type = context.api.expr_checker.analyze_external_member_access(
            attr_name, t, context.context
        )
        default_attr_type = context.default_attr_type.copy_modified(
            args=(context.type.args[0], attr_type)
        )
        _set_lens_method_types(default_attr_type)
        return default_attr_type
    args_repr = ", ".join(str(a) for a in context.type.args)
    type_repr = f'pfun.lens.Lens[{args_repr}]'
    context.api.fail(
        f'"{type_repr}" has no attribute "{attr_name}"', context.context
    )
    any_t = AnyType(TypeOfAny.special_form)
    return context.default_attr_type.copy_modified(args=(any_t, any_t))


def _set_lens_method_types(lens: Instance) -> None:
    arg_type = lens.args[0]
    t_def = _type_var_def('A', 'pfun.lens', upper_bound=arg_type, variance=COVARIANT)
    t_var = TypeVarType(t_def)
    __call__ = lens.type.names['__call__']
    __ror__ = lens.type.names['__ror__']
    _set_method_type_vars(__ror__, t_var, t_def)
    _set_method_type_vars(__call__, t_var, t_def)


def _set_method_type_vars(method, t_var, t_def):
    old_t_var = method.node.type.arg_types[1]
    translator = ReplaceTypeVar(target_t_var=old_t_var, replacement_t_var=t_var)
    any_t = AnyType(TypeOfAny.special_form)
    method.node.type.arg_types[0] = method.node.type.arg_types[0].copy_modified(args=(any_t, method.node.type.arg_types[0].args[1]))
    method.node.type = method.node.type.copy_modified(variables=[t_def])
    method.node.type = method.node.type.accept(translator)


def _lens_getitem_hook(context: MethodContext) -> Type:
    t = context.type.args[-1]
    args_repr = ", ".join(str(a) for a in context.type.args)
    type_repr = f'pfun.lens.Lens[{args_repr}]'
    if context.api.expr_checker.has_member(t, '__getitem__'):
        getitem_type = context.api.expr_checker.analyze_external_member_access(
            '__getitem__', t, context.context
        )
        result_type, _ = context.api.expr_checker.check_call(
            getitem_type,
            context.args[0],
            context.arg_kinds[0],
            context.context,
            object_type=t,
            callable_name=f'{type_repr}.__getitem__'
        )
        default_return_type = context.default_return_type.copy_modified(
            args=(context.default_return_type.args[0], result_type)
        )
        _set_lens_method_types(default_return_type)
        return default_return_type
    context.api.fail(
        f'Value of type "{type_repr}" is not indexable', context.context
    )
    any_t = AnyType(TypeOfAny.special_form)
    return context.default_return_type.copy_modified(args=(any_t, any_t))


def _lens_hook(context: FunctionContext) -> Type:
    if not context.arg_types[0]:
        return context.default_return_type
    arg_type = context.arg_types[0][0]
    if not hasattr(arg_type, 'is_type_obj') or not arg_type.is_type_obj():
        return context.default_return_type
    if isinstance(arg_type, Overloaded):
        arg_type = arg_type.items()[0]
    arg_type = arg_type.ret_type
    return context.default_return_type.copy_modified(
        args=(arg_type,)
    )


def _curry_call_hook(context: MethodContext) -> Type:
    any_t = AnyType(TypeOfAny.special_form)
    default_signature = context.default_signature.copy_modified(
        ret_type=any_t,
        arg_types=[any_t, any_t],
        arg_kinds=[ARG_STAR, ARG_STAR2],
        arg_names=['args', 'kwargs']
    )
    callee = context.type.args[0]
    if isinstance(callee, AnyType):
        return default_signature
    if isinstance(callee, Instance):
        variables = {}
        callee = analyze_member_access(
            '__call__',
            callee,
            context.context,
            is_lvalue=False,
            is_super=False,
            is_operator=True,
            msg=context.api.msg,
            original_type=callee,
            chk=context.api,
            in_literal_context=context.api.expr_checker.is_literal_context()
        )
    else:
        variables = {abs(v.id.raw_id): v for v in callee.variables}
    expr = context.context
    if isinstance(expr, CallExpr):
        arg_kinds = expr.arg_kinds
        arg_names = expr.arg_names
        args = expr.args
    else:
        arg_kinds = [ARG_POS]
        arg_names = [None]
        args = context.args[0]
    actual_to_formal = map_formals_to_actuals(
        arg_kinds,
        arg_names,
        callee.arg_kinds,
        callee.arg_names,
        lambda i: f.arg_types[i]
    )
    applied_args = set(i for m in actual_to_formal for i in m)
    unapplied_args = set(range(len(callee.arg_kinds))) - applied_args
    applied_arg_kinds = [callee.arg_kinds[i] for i in applied_args]
    applied_arg_names = [callee.arg_names[i] for i in applied_args]
    applied_arg_types = [callee.arg_types[i] for i in applied_args]
    unapplied_arg_kinds = [callee.arg_kinds[i] for i in unapplied_args]
    unapplied_arg_names = [callee.arg_names[i] for i in unapplied_args]
    unapplied_arg_types = [callee.arg_types[i] for i in unapplied_args]
    if variables:
        applied_variables = set(variables[abs(v.id.raw_id)] for t in applied_arg_types for v in get_type_vars(t))
        unapplied_variables = set(variables[abs(v.id.raw_id)] for t in unapplied_arg_types for v in get_type_vars(t)) - applied_variables
        unapplied_variables = unapplied_variables | (set(variables[abs(v.id.raw_id)] for v in get_type_vars(callee.ret_type)) - applied_variables)
    else:
        applied_variables = unapplied_variables = []
    if all(
        arg_kind in (ARG_OPT, ARG_STAR, ARG_STAR2, ARG_NAMED_OPT)
        for arg_kind in unapplied_arg_kinds
    ):
        ret_type = callee.ret_type
    else:   
        arg = CallableType(
            arg_kinds=unapplied_arg_kinds,
            arg_types=unapplied_arg_types,
            arg_names=unapplied_arg_names,
            ret_type=callee.ret_type,
            fallback=callee.fallback,
            name=callee.name,
            variables=list(unapplied_variables)
        )
        ret_type = context.type.copy_modified(args=[arg])
        add_method_to_instance(
            ret_type,
            arg,
            '__call__',
            context.api.named_type('builtins.function')
        )
    return default_signature.copy_modified(arg_types=applied_arg_types, arg_kinds=applied_arg_kinds, arg_names=applied_arg_names, ret_type=ret_type, variables=list(applied_variables))


def add_method_to_class(
    fallback: Type,
    cls: ClassDef,
    name: str,
    args: t.List[Argument],
    return_type: Type,
    self_type: t.Optional[Type] = None,
    variables = ()
) -> None:
    """Adds a new method to a class definition. Copied from
    https://github.com/python/mypy/blob/master/mypy/plugins/common.py
    """
    info = cls.info

    # First remove any previously generated methods with the same name
    # to avoid clashes and problems in the semantic analyzer.
    if name in info.names:
        sym = info.names[name]
        if sym.plugin_generated and isinstance(sym.node, FuncDef):
            cls.defs.body.remove(sym.node)

    self_type = self_type or fill_typevars(info)

    args = [Argument(Var('self'), self_type, None, ARG_POS)] + args
    arg_types, arg_names, arg_kinds = [], [], []
    for arg in args:
        assert arg.type_annotation, 'All arguments must be fully typed.'
        arg_types.append(arg.type_annotation)
        arg_names.append(arg.variable.name)
        arg_kinds.append(arg.kind)

    signature = CallableType(
        arg_types, arg_kinds, arg_names, return_type, fallback
    )
    signature.variables = variables

    func = FuncDef(name, args, Block([PassStmt()]))
    func.info = info
    func.type = set_callable_name(signature, func)
    func._fullname = info.fullname + '.' + name
    func.line = info.line
    # NOTE: we would like the plugin generated node to dominate, but we still
    # need to keep any existing definitions so they get semantically analyzed.
    if name in info.names:
        # Get a nice unique name instead.
        r_name = get_unique_redefinition_name(name, info.names)
        info.names[r_name] = info.names[name]

    info.names[name] = SymbolTableNode(MDEF, func, plugin_generated=True)
    info.defn.defs.body.append(func)


def add_method_to_instance(
    instance: Instance, f: CallableType, name: str, fallback
) -> None:
    if name in instance.type.names:
        del instance.type.names[name]
    instance.type.defn.defs.body = [
        node for node in instance.type.defn.defs.body
        if hasattr(node, 'name') and node.name != name
    ]
    arg_types = f.arg_types if hasattr(
        f, 'arg_types'
    ) else [AnyType(TypeOfAny.special_form)] * len(f.arg_kinds)
    arguments = [
        Argument(Var(name if name else f'a{i}', t), t, None, kind)
        for i, (t, kind,
                name) in enumerate(zip(arg_types, f.arg_kinds, f.arg_names))
    ]
    ret_type = f.ret_type if hasattr(f, 'ret_type') else AnyType(
        TypeOfAny.special_form
    )
    add_method_to_class(
        fallback, instance.type.defn, name, arguments, ret_type, variables=f.variables
    )


def _empty_curry_instance(args, fallback):
    defn = ClassDef(name='Curry', defs=Block([]))
    defn.fullname = 'pfun.functions.Curry'
    instance = Instance(
        typ=TypeInfo(names={}, defn=defn, module_name='pfun.functions'),
        args=args
    )
    any_t = AnyType(TypeOfAny.special_form)
    arg_types = [any_t, any_t]
    arg_kinds = [ARG_STAR, ARG_STAR2]
    arg_names = ['args', 'kwargs']
    instance.type.defn.info = instance.type
    __call__ = CallableType(arg_types, arg_kinds, arg_names, any_t, fallback)
    __ror__ = CallableType([any_t], [ARG_POS], ['x'], any_t, fallback)
    add_method_to_instance(instance, __call__, '__call__', fallback)
    add_method_to_instance(instance, __ror__, '__ror__', fallback)
    calculate_mro(instance.type)
    return instance


def _curry_type_analyze_hook(context):
    fallback = context.api.named_type('builtins.function')
    any_t = AnyType(TypeOfAny.special_form)
    if not context.type.args:
        return _empty_curry_instance([any_t], fallback)
    f = context.type.args[0]
    f_analyzed = context.api.anal_type(f)
    curry_instance = _empty_curry_instance([f_analyzed], fallback)
    if isinstance(f_analyzed, TypeVarType):
        return curry_instance
    elif isinstance(f_analyzed, AnyType):
        return curry_instance
    add_method_to_instance(
        curry_instance, f_analyzed, '__call__', f_analyzed.fallback
    )
    context.api.api.add_plugin_dependency(curry_instance.type.fullname)
    return context.api.anal_type(curry_instance)


def _curry_hook(context):
    t = context.default_return_type
    __call__ = context.arg_types[0][0]
    __call__ = _get_callable_type(__call__, context)
    if isinstance(__call__, Instance) and __call__.type.fullname == 'pfun.functions.Curry':
        return __call__
    any_t = AnyType(TypeOfAny.special_form) 
    __ror__ = CallableType(
        [any_t], [ARG_POS], ['x'],
        any_t,
        context.api.named_type('builtins.function')
    )
    add_method_to_instance(
        t, __call__, '__call__', context.api.named_type('builtins.function')
    )
    add_method_to_instance(
        t, __ror__, '__ror__', context.api.named_type('builtins.function')
    )
    return t.copy_modified(args=[__call__])



def _curry_instance(f: CallableType) -> Instance:
    instance = _empty_curry_instance((f,), f.fallback)
    __call__ = _curry_signature(f)
    add_method_to_instance(instance, __call__, '__call__', f.fallback)
    return instance



def _curry_signature(f: CallableType) -> CallableType:
    def variable_id(v: TypeVarDef) -> int:
        return abs(v.id.raw_id)
    
    def filter_args_by_kind(kinds: t.List[int]) -> t.Tuple[str, int, Type]:
        return zip(*[
            (arg_name, arg_kind, arg_type) 
            for arg_name, arg_kind, arg_type 
            in zip(f.arg_names, f.arg_kinds, f.arg_types) 
            if arg_kind in kinds
        ])
    
    def get_variables(arg_types: t.List[Type]) -> t.Set[TypeVarDef]:
        return {variables[variable_id(v)] 
                for t in arg_types 
                for v in get_type_vars(t)}

    optional_kinds = (ARG_OPT, ARG_STAR2)
    required_kinds = (ARG_POS, ARG_STAR)
    all_optional = all(k in optional_kinds for k in f.arg_kinds)
    unary_or_nullary = len(f.arg_names) < 2
    if unary_or_nullary or all_optional:
        return f
    overloads = [f]
    variable_id = lambda v: abs(v.id.raw_id)
    variables = {variable_id(v): v for v in f.variables}
    (optional_arg_names,
     optional_arg_kinds,
     optional_arg_types) = filter_args_by_kinds(optional_kinds)
    optional_variables = get_variables(required_arg_types)
    (required_arg_names,
     required_arg_kinds,
     required_arg_types) = filter_args_by_kinds(required_kinds)
    required_variables = get_variables(required_arg_types)
    if optional_arg_kinds:
        return_f = f.copy_modified(arg_types=required_arg_types, 
                                   arg_kinds=required_arg_kinds,
                                   arg_names=required_arg_names,
                                   variables=required_varablies)
        overload = f.copy_modified(arg_types=optional_arg_types,
                                   arg_kinds=optional_arg_kinds,
                                   arg_names=optional_arg_names,
                                   variables=optional_variables,
                                   ret_type=_curry_instance(return_f))
        overloads.append(overload)
    first_arg_name, *rest_arg_names = required_arg_names
    first_arg_kind, *rest_arg_kinds = required_arg_kinds
    first_arg_type, *rest_arg_types = required_arg_types
    first_arg_variables = get_variables([first_arg_type])
    rest_variables = get_variables(rest_arg_types)
    return_f = f.copy_modified(arg_types=rest_arg_types, arg_names=rest_arg_names, arg_kinds=rest_arg_kinds, variables=rest_variables)
    overload = f.copy_modified(arg_types=[first_arg_type], arg_names=[first_arg_name], arg_kinds=[first_arg_kind], variables=first_arg_variables, ret_type=_curry_instance(return_f))
    overloads.append(overload)
    return Overloaded(overloads)
    

    


class PFun(Plugin):
    def get_type_analyze_hook(self, fullname: str):
        if fullname == 'pfun.functions.Curry':
            return _curry_type_analyze_hook

    def get_function_hook(self, fullname: str
                          ) -> t.Optional[t.Callable[[FunctionContext], Type]]:
        if fullname in (
            'pfun.effect.catch',
            'pfun.effect.catch_cpu_bound',
            'pfun.effect.catch_io_bound'
        ):
            return _effect_catch_hook
        if fullname == _COMPOSE:
            return _compose_hook
        if fullname in (
            _MAYBE, _RESULT, _EITHER, _EITHER_CATCH, 'pfun.effect.catch_all'
        ):
            return _variadic_decorator_hook
        if fullname in (
            'pfun.effect.combine',
            'pfun.effect.combine_cpu_bound',
            'pfun.effect.combine_io_bound'
        ):
            return _combine_hook
        if fullname == 'pfun.lens.lens':
            return _lens_hook
        if fullname == 'pfun.functions.curry':
            return _curry_hook
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
        if fullname in (
            'pfun.effect.catch.__call__',
            'pfun.effect.catch_io_bound.__call__',
            'pfun.effect.catch_cpu_bound.__call__'
        ):
            return _effect_catch_call_hook
        if fullname in (
            'pfun.effect.lift.__call__',
            'pfun.effect.lift_io_bound.__call__',
            'pfun.effect.lift_cpu_bound.__call__'
        ):
            return _effect_lift_call_hook
        if fullname in (
            'pfun.lens.RootLens.__getitem__', 'pfun.lens.Lens.__getitem__'
        ):
            return _lens_getitem_hook

    def get_attribute_hook(self, fullname: str):
        if fullname.startswith('pfun.lens.RootLens'
                               ) and not fullname.endswith('__path'):
            return _lens_getattr_hook(fullname)

    def get_method_signature_hook(self, fullname: str):
        if fullname in (
            'pfun.effect.lift.__call__',
            'pfun.effect.lift_cpu_bound.__call__',
            'pfun.effect.lift_io_bound.__call__'
        ):
            return _effect_lift_call_signature_hook
        if fullname == 'pfun.functions.Curry.__call__':
            return _curry_call_hook
        if fullname == 'pfun.functions.Curry.__or__':
            return _curry_call_hook

    def get_base_class_hook(self, fullname: str):
        return _immutable_hook


def plugin(_):
    return PFun
