# Copyright (c) 2022, NVIDIA CORPORATION.

from numba import types
from numba.core import cgutils
from numba.core.extending import lower_builtin
from numba.core.typing import signature as nb_signature
from numba.cuda.cudaimpl import lower as cuda_lower

from cudf.core.udf.groupby_function import (
    Group,
    GroupType,
    call_cuda_functions,
)


def lowering_function(context, builder, sig, args, function):
    retty = sig.return_type

    grp = cgutils.create_struct_proxy(sig.args[0])(
        context, builder, value=args[0]
    )
    grp_type = sig.args[0]

    group_dataty = grp_type.group_data_type
    group_data_ptr = builder.alloca(grp.group_data.type)
    builder.store(grp.group_data, group_data_ptr)

    func = call_cuda_functions[function][grp_type.group_scalar_type]

    return context.compile_internal(
        builder,
        func,
        nb_signature(retty, group_dataty, grp_type.size_type),
        (builder.load(group_data_ptr), grp.size),
    )


@lower_builtin(Group, types.Array, types.int64, types.Array)
def group_constructor(context, builder, sig, args):
    group_data, size, index = args

    grp = cgutils.create_struct_proxy(sig.return_type)(context, builder)

    arr_group_data = cgutils.create_struct_proxy(sig.args[0])(
        context, builder, value=group_data
    )
    group_data_ptr = arr_group_data.data

    arr_index = cgutils.create_struct_proxy(sig.args[2])(
        context, builder, value=index
    )
    index_ptr = arr_index.data

    grp.group_data = group_data_ptr
    grp.index = index_ptr
    grp.size = size

    return grp._getvalue()


@cuda_lower("GroupType.max", GroupType(types.int64))
@cuda_lower("GroupType.max", GroupType(types.float64))
def cuda_Group_max(context, builder, sig, args):
    return lowering_function(context, builder, sig, args, "max")


@cuda_lower("GroupType.min", GroupType(types.int64))
@cuda_lower("GroupType.min", GroupType(types.float64))
def cuda_Group_min(context, builder, sig, args):
    return lowering_function(context, builder, sig, args, "min")


@cuda_lower("GroupType.size", GroupType(types.int64))
@cuda_lower("GroupType.size", GroupType(types.float64))
def cuda_Group_size(context, builder, sig, args):
    grp = cgutils.create_struct_proxy(sig.args[0])(
        context, builder, value=args[0]
    )
    return grp.size


@cuda_lower("GroupType.count", GroupType(types.int64))
@cuda_lower("GroupType.count", GroupType(types.float64))
def cuda_Group_count(context, builder, sig, args):
    grp = cgutils.create_struct_proxy(sig.args[0])(
        context, builder, value=args[0]
    )
    return grp.size


@cuda_lower("GroupType.sum", GroupType(types.int64))
@cuda_lower("GroupType.sum", GroupType(types.float64))
def cuda_Group_sum(context, builder, sig, args):
    return lowering_function(context, builder, sig, args, "sum")


@cuda_lower("GroupType.mean", GroupType(types.int64))
@cuda_lower("GroupType.mean", GroupType(types.float64))
def cuda_Group_mean(context, builder, sig, args):
    return lowering_function(context, builder, sig, args, "mean")


@cuda_lower("GroupType.std", GroupType(types.int64))
@cuda_lower("GroupType.std", GroupType(types.float64))
def cuda_Group_std(context, builder, sig, args):
    return lowering_function(context, builder, sig, args, "std")


@cuda_lower("GroupType.var", GroupType(types.int64))
@cuda_lower("GroupType.var", GroupType(types.float64))
def cuda_Group_var(context, builder, sig, args):
    return lowering_function(context, builder, sig, args, "var")


@cuda_lower("GroupType.idxmax", GroupType(types.int64, types.int64))
@cuda_lower("GroupType.idxmax", GroupType(types.float64, types.int64))
def cuda_Group_idxmax(context, builder, sig, args):
    retty = sig.return_type

    grp = cgutils.create_struct_proxy(sig.args[0])(
        context, builder, value=args[0]
    )
    grp_type = sig.args[0]

    group_dataty = grp_type.group_data_type
    group_data_ptr = builder.alloca(grp.group_data.type)
    builder.store(grp.group_data, group_data_ptr)

    index_dataty = grp_type.group_index_type
    index_ptr = builder.alloca(grp.index.type)
    builder.store(grp.index, index_ptr)

    func = call_cuda_functions["idxmax"][grp_type.group_scalar_type]

    return context.compile_internal(
        builder,
        func,
        nb_signature(retty, group_dataty, index_dataty, grp_type.size_type),
        (builder.load(group_data_ptr), builder.load(index_ptr), grp.size),
    )


@cuda_lower("GroupType.idxmin", GroupType(types.int64, types.int64))
@cuda_lower("GroupType.idxmin", GroupType(types.float64, types.int64))
def cuda_Group_idxmin(context, builder, sig, args):
    retty = sig.return_type

    grp = cgutils.create_struct_proxy(sig.args[0])(
        context, builder, value=args[0]
    )
    grp_type = sig.args[0]

    group_dataty = grp_type.group_data_type
    group_data_ptr = builder.alloca(grp.group_data.type)
    builder.store(grp.group_data, group_data_ptr)

    index_dataty = grp_type.group_index_type
    index_ptr = builder.alloca(grp.index.type)
    builder.store(grp.index, index_ptr)

    func = call_cuda_functions["idxmin"][grp_type.group_scalar_type]

    return context.compile_internal(
        builder,
        func,
        nb_signature(retty, group_dataty, index_dataty, grp_type.size_type),
        (builder.load(group_data_ptr), builder.load(index_ptr), grp.size),
    )
