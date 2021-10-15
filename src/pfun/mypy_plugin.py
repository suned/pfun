#  type: ignore

import typing as t

from mypy import checkmember, infer
from mypy.argmap import map_actuals_to_formals
from mypy.checker import TypeChecker
from mypy.expandtype import freshen_function_type_vars
from mypy.mro import MroError, calculate_mro
from mypy.nodes import (ARG_NAMED, ARG_NAMED_OPT, ARG_OPT, ARG_POS, ARG_STAR,
                        ARG_STAR2, COVARIANT, INVARIANT, Block, ClassDef,
                        NameExpr, TypeInfo)
from mypy.plugin import (AnalyzeTypeContext, AttributeContext, ClassDefContext,
                         FunctionContext, FunctionSigContext, MethodContext,
                         MethodSigContext, Plugin)
from mypy.plugins.dataclasses import DataclassTransformer
from mypy.type_visitor import TypeTranslator
from mypy.types import (AnyType, CallableType, Instance, Overloaded, Type,
                        TypeAliasType, TypeOfAny, TypeVarDef, TypeVarId,
                        TypeVarType, UninhabitedType, UnionType,
                        get_proper_type)
from mypy.typevars import has_no_typevars

from .functions import curry

_CURRY = 'pfun.functions.curry'
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
        return [v if v != self.target_t_def else self.replacement_t_def
                for v in variables]

    def visit_type_var(self, t: TypeVarType):
        return t if t != self.target_t_var else self.replacement_t_var


class IllegalIntersection(Exception):
    pass


class TranslateIntersection(TypeTranslator):
    def __init__(self, api, context, inferred=False):
        self.api = api
        self.context = context
        self.inferred = inferred

    def get_bases(self, base, seen):
        if isinstance(base, TypeVarType):
            return [base]
        if 'pfun.Intersection' in base.type.fullname:
            for b in base.type.bases:
                if b not in seen:
                    seen = seen + self.get_bases(b, seen)
            return seen
        elif base.type.fullname == 'builtins.object':
            return []
        return [base]

    def visit_type_alias_type(self, t: TypeAliasType) -> Type:
        t = get_proper_type(t)
        return t.accept(self)

    def visit_instance(self, t: Instance) -> Type:
        if 'pfun.Intersection' == t.type.fullname:
            args = [get_proper_type(arg) for arg in t.args]
            if any(isinstance(arg, AnyType) for arg in args):
                return AnyType(TypeOfAny.special_form)
            if all(hasattr(arg, 'type') and
                   arg.type.fullname == 'builtins.object' for arg in args):
                return args[0]
            is_typevar = lambda arg: isinstance(arg, TypeVarType)
            has_type_attr = lambda arg: hasattr(arg, 'type')
            is_protocol = lambda arg: arg.type.is_protocol
            is_object = lambda arg: arg.type.fullname == 'builtins.object'
            if not all(is_typevar(arg) or
                       has_type_attr(arg) and
                       (is_protocol(arg) or is_object(arg))
                       for arg in args):
                s = str(t)
                if self.inferred:
                    msg = (f'All arguments to "Intersection" '
                           f'must be protocols but inferred "{s}"')
                else:
                    msg = (f'All arguments to "Intersection" '
                           f'must be protocols, but got "{s}"')
                self.api.msg.fail(msg, self.context)
                return AnyType(TypeOfAny.special_form)
            if not has_no_typevars(t):
                return t
            bases = []
            for arg in args:
                if arg in bases:
                    continue
                bases.extend(self.get_bases(arg, []))
            if len(bases) == 1:
                return bases[0]
            bases_repr = ', '.join([repr(base) for base in bases])
            name = f'Intersection[{bases_repr}]'
            defn = ClassDef(
                name,
                Block([]),
                [],
                [NameExpr(arg.name)
                 if isinstance(arg, TypeVarType)
                 else NameExpr(arg.type.fullname) for arg in args],
                None,
                []
            )
            defn.fullname = f'pfun.{name}'
            info = TypeInfo({}, defn, '')
            info.is_protocol = True
            info.is_abstract = True
            info.bases = bases
            attrs = []
            for base in bases:
                if isinstance(base, TypeVarType):
                    continue
                attrs.extend(base.type.abstract_attributes)
            info.abstract_attributes = attrs
            try:
                calculate_mro(info)
            except MroError:
                self.api.msg.fail(
                    'Cannot determine consistent method resolution '
                    'order (MRO) for "%s"' % defn.fullname, self.context)
                return AnyType(TypeOfAny.special_form)
            return Instance(info, [])

        return super().visit_instance(t)


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
        # argument was not callable type or function
        return context.default_return_type

    if len(function.arg_types) < 2:
        # nullary or unary function: nothing to do
        return function

    type_vars = {var.fullname: var for var in function.variables}

    def get_variables(*types):
        def collect_variables(*ts):
            variables = []
            for type_ in ts:
                if isinstance(type_, TypeVarType):
                    variables.append(type_)
                if hasattr(type_, 'args'):
                    variables += get_variables(*type_.args)
                if isinstance(type_, CallableType):
                    variables += get_variables(
                        type_.ret_type, *type_.arg_types
                    )
                if isinstance(type_, UnionType):
                    variables += get_variables(*type_.items)
            return variables

        return set(type_vars[v.fullname] for v in collect_variables(*types))

    args = tuple(
        zip(function.arg_types, function.arg_kinds, function.arg_names)
    )
    optional_args = tuple(
        filter(lambda a: a[1] in (ARG_OPT, ARG_NAMED_OPT, ARG_STAR2), args)
    )
    positional_args = tuple(
        filter(lambda a: a[1] in (ARG_POS, ARG_NAMED, ARG_STAR), args)
    )

    if not positional_args:
        # no positional args: nothing to do
        return function
    opt_arg_types, opt_arg_kinds, opt_arg_names = (tuple(zip(*optional_args))
                                                   if optional_args
                                                   else ((), (), ()))
    pos_arg_types, pos_arg_kinds, pos_arg_names = tuple(zip(*positional_args))
    arg_type, *arg_types = pos_arg_types
    arg_name, *arg_names = pos_arg_names
    arg_kind, *arg_kinds = pos_arg_kinds
    return_type = function.ret_type

    opt_variables = get_variables(*opt_arg_types)
    variables = get_variables(arg_type)
    if len(pos_arg_types) == 1:
        variables |= get_variables(return_type)
        ret_type = return_type
    else:
        ret_type = AnyType(TypeOfAny.special_form)
    functions = [
        CallableType(
            arg_types=[arg_type],
            arg_kinds=[arg_kind],
            arg_names=[arg_name],
            ret_type=ret_type,
            fallback=function.fallback,
            variables=list(variables)
        )
    ]

    remaining_args = zip(arg_types, arg_kinds, arg_names)
    for i, (arg_type, kind, name) in enumerate(remaining_args):
        variables = get_variables(arg_type)
        if i == len(arg_types) - 1:
            variables |= get_variables(return_type)
            ret_type = return_type
        else:
            ret_type = AnyType(TypeOfAny.special_form)
        variables -= set.union(*[set(f.variables) for f in functions])
        if kind == ARG_STAR:
            last_f = functions[i]
            functions[i] = last_f.copy_modified(
                arg_types=last_f.arg_types + [arg_type],
                arg_kinds=last_f.arg_kinds + [kind],
                arg_names=last_f.arg_names + [name],
                variables=list(sorted(variables, key=str)),
                ret_type=ret_type
            )
        else:
            functions.append(
                CallableType(
                    arg_types=[arg_type],
                    arg_kinds=[kind],
                    arg_names=[name],
                    ret_type=ret_type,
                    fallback=function.fallback,
                    variables=list(sorted(variables, key=str))
                )
            )

    def merge(fs):
        if len(fs) == 1:
            return fs[0]
        first, next_, *rest = fs
        first.ret_type = next_
        for f in rest:
            next_.ret_type = f
            next_ = f
        return first

    merged = merge(functions)
    if optional_args:
        mod_functions = [
            f.copy_modified(
                variables=list(
                    sorted(set(f.variables) - opt_variables, key=str)
                )
            )
            for f in functions
        ]
        mod_merged = merge(mod_functions)
        with_opts = CallableType(
            arg_types=list(opt_arg_types),
            arg_kinds=list(opt_arg_kinds),
            arg_names=list(opt_arg_names),
            ret_type=mod_merged,
            fallback=function.fallback,
            variables=list(sorted(opt_variables, key=str))
        )
        return Overloaded([merged, function, with_opts])
    return Overloaded([merged, function])


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
    name: str,
    module: str,
    upper_bound,
    values=(),
    meta_level=0,
    variance=INVARIANT
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
    transformer._freeze(attributes if attributes is not None else [])


def _combine_error_types(ts: t.List[Type]) -> UnionType:
    without_noreturn = list({e for e in ts
                             if not isinstance(e, UninhabitedType)})
    return UnionType.make_union(sorted(without_noreturn, key=str))


def _combine_hook(context: FunctionContext):
    error_types = []
    env_types = []
    pos_map_arg_types = []
    var_map_arg_types = []
    map_arg_kinds = []
    variadic = False
    try:
        for arg_type, arg_kind in zip(context.arg_types[0],
                                      context.arg_kinds[0]):
            if arg_kind == ARG_STAR:
                # assume iterable
                effect_type = arg_type.args[0]
                if not variadic:
                    map_arg_kinds.append(ARG_STAR)
                variadic = True
            else:
                effect_type = arg_type
                if not variadic:
                    map_arg_kinds.append(arg_kind)
            env_type, error_type, result_type = get_proper_type(
                effect_type
            ).args
            env_types.append(env_type)
            error_types.append(error_type)
            if variadic:
                var_map_arg_types.append(result_type)
            else:
                pos_map_arg_types.append(result_type)

        map_return_type_def = _type_var_def(
            'R1', 'pfun.effect', context.api.named_type('builtins.object')
        )
        map_return_type = TypeVarType(map_return_type_def)
        var_arg_types = ([UnionType.make_union(list(set(var_map_arg_types)))]
                         if var_map_arg_types else [])
        arg_types = pos_map_arg_types + var_arg_types
        map_function_type = CallableType(
            arg_types=arg_types,
            arg_kinds=map_arg_kinds,
            arg_names=[None] * len(arg_types),
            ret_type=map_return_type,
            variables=[map_return_type_def],
            fallback=context.api.named_type('builtins.function')
        )
        ret_type = context.default_return_type.ret_type
        combined_error_type = _combine_error_types(error_types)
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
            combined_env_type = _create_intersection(env_types,
                                                     context.context,
                                                     context.api)
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
        r = _create_intersection(rs, context.context, context.api)
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


def _set_lens_method_types(lens: Instance) -> None:
    arg_type = lens.args[0]
    t_def = _type_var_def(
        'A',
        'pfun.lens',
        upper_bound=arg_type,
        variance=COVARIANT
    )
    t_var = TypeVarType(t_def)
    __call__ = lens.type.names['__call__']
    _set_method_type_vars(__call__, t_var, t_def)


def _set_method_type_vars(method, t_var, t_def):
    ret_type = method.node.type.ret_type
    old_t_var = ret_type.ret_type
    translator = ReplaceTypeVar(
        target_t_var=old_t_var,
        replacement_t_var=t_var
    )
    ret_type = ret_type.accept(translator)
    ret_type = ret_type.copy_modified(variables=[t_def])
    method.node.type = method.node.type.copy_modified(ret_type=ret_type)


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


def _create_intersection(args, context, api):
    defn = ClassDef('Intersection', Block([]))
    defn.fullname = 'pfun.Intersection'
    info = TypeInfo({}, defn, 'pfun')
    info.is_protocol = True
    calculate_mro(info)
    i = Instance(info, args, line=context.line, column=context.column)
    intersection_translator = TranslateIntersection(api, i)
    return i.accept(intersection_translator)


def _intersection_analyze_hook(context):
    args = [context.api.anal_type(arg) for arg in context.type.args]
    return _create_intersection(args, context.context, context.api.api)


def _intersection_hook(context: FunctionSigContext):
    has_intersection = 'pfun.Intersection' in str(context.default_signature)
    is_generic = context.default_signature.is_generic()
    if not has_intersection or not is_generic:
        return context.default_signature
    formal_to_actual = map_actuals_to_formals(
        context.context.arg_kinds,
        context.context.arg_names,
        context.default_signature.arg_kinds,
        context.default_signature.arg_names,
        lambda i: context.api.expr_checker.accept(context.args[0][i])
    )
    callee = freshen_function_type_vars(context.default_signature)
    callee = (context
              .api
              .expr_checker
              .infer_function_type_arguments_using_context(callee,
                                                           context.context))
    args = [arg for args in context.args for arg in args]
    callee = context.api.expr_checker.infer_function_type_arguments(
        callee, args,
        context.context.arg_kinds,
        formal_to_actual,
        context.context
    )
    intersection_translator = TranslateIntersection(context.api,
                                                    context.context,
                                                    inferred=True)
    translated = callee.accept(intersection_translator)
    return translated


C = t.TypeVar('C')
T = t.TypeVar('T')
Hook = t.Optional[t.Callable[[C], T]]


class PFun(Plugin):
    def get_function_hook(self, fullname: str
                          ) -> Hook[FunctionContext, Type]:
        if fullname in ('pfun.effect.catch',
                        'pfun.effect.catch_cpu_bound',
                        'pfun.effect.catch_io_bound'):
            return _effect_catch_hook
        if fullname == _CURRY:
            return _curry_hook
        if fullname == _COMPOSE:
            return _compose_hook
        if fullname in (
            _MAYBE,
            _RESULT,
            _EITHER,
            _EITHER_CATCH,
            'pfun.effect.catch_all',
            'pfun.effect.purify',
            'pfun.effect.purify_io_bound',
            'pfun.effect.purify_cpu_bound'
        ):
            return _variadic_decorator_hook
        if fullname in ('pfun.effect.combine',
                        'pfun.effect.combine_cpu_bound',
                        'pfun.effect.combine_io_bound',
                        'pfun.effect.combine_async'):
            return _combine_hook
        if fullname == 'pfun.lens.lens':
            return _lens_hook
        return None

    def get_function_signature_hook(self, fullname: str
                                    ) -> Hook[FunctionSigContext,
                                              CallableType]:
        return _intersection_hook

    def get_method_hook(self, fullname: str):
        if fullname in ('pfun.effect.catch.__call__',
                        'pfun.effect.catch_io_bound.__call__',
                        'pfun.effect.catch_cpu_bound.__call__'):
            return _effect_catch_call_hook
        if fullname in ('pfun.effect.lift.__call__',
                        'pfun.effect.lift_io_bound.__call__',
                        'pfun.effect.lift_cpu_bound.__call__',
                        'pfun.effect.lift_async.__call__'):
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
        if fullname in ('pfun.effect.lift.__call__',
                        'pfun.effect.lift_cpu_bound.__call__',
                        'pfun.effect.lift_io_bound.__call__',
                        'pfun.effect.lift_async.__call__'):
            return _effect_lift_call_signature_hook
        return _intersection_hook

    def get_base_class_hook(self, fullname: str):
        return _immutable_hook

    def get_type_analyze_hook(self, fullname: str
                              ) -> Hook[AnalyzeTypeContext, Type]:
        if fullname == 'pfun.Intersection':
            return _intersection_analyze_hook


def plugin(_):
    return PFun
