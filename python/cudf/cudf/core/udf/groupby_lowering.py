# Copyright (c) 2022-2023, NVIDIA CORPORATION.

from functools import partial

from numba import types
from numba.core import cgutils
from numba.core.extending import lower_builtin
from numba.core.typing import signature as nb_signature
from numba.cuda.cudaimpl import lower as cuda_lower

from cudf.core.udf.groupby_typing import (
    SUPPORTED_GROUPBY_NUMBA_TYPES,
    Group,
    GroupType,
    call_cuda_functions,
    index_default_type,
)


def lowering_function(context, builder, sig, args, function):
    """
    Instruction boilerplate used for calling a groupby reduction
    __device__ function. Centers around a forward declaration of
    this function and adds the pre/post processing instructions
    necessary for calling it.
    """
    # return type
    retty = sig.return_type

    # a variable logically corresponding to the calling `Group`
    grp = cgutils.create_struct_proxy(sig.args[0])(
        context, builder, value=args[0]
    )

    # what specific (numba) GroupType
    grp_type = sig.args[0]
    group_dataty = grp_type.group_data_type

    # logically take the address of the group's data pointer
    group_data_ptr = builder.alloca(grp.group_data.type)
    builder.store(grp.group_data, group_data_ptr)

    # obtain the correct forward declaration from registry
    type_key = (sig.return_type, grp_type.group_scalar_type)
    func = call_cuda_functions[function][type_key]

    # insert the forward declaration and return its result
    # pass it the data pointer and the group's size
    return context.compile_internal(
        builder,
        func,
        nb_signature(retty, group_dataty, grp_type.size_type),
        (builder.load(group_data_ptr), grp.size),
    )


@lower_builtin(Group, types.Array, types.int64, types.Array)
def group_constructor(context, builder, sig, args):
    """
    Instruction boilerplate used for instantiating a Group
    struct from a data pointer, an index pointer, and a size
    """

    group_data, size, index = args

    # a variable logically corresponding to the calling `Group`
    grp = cgutils.create_struct_proxy(sig.return_type)(context, builder)

    # the group data array and its pointer
    arr_group_data = cgutils.create_struct_proxy(sig.args[0])(
        context, builder, value=group_data
    )
    group_data_ptr = arr_group_data.data

    # the group index array and its pointer
    arr_index = cgutils.create_struct_proxy(sig.args[2])(
        context, builder, value=index
    )
    index_ptr = arr_index.data

    # fill the struct explicitly
    grp.group_data = group_data_ptr
    grp.index = index_ptr
    grp.size = size

    # return the struct by value
    return grp._getvalue()


def cuda_Group_idx_max_or_min(context, builder, sig, args, function):
    """
    Instruction boilerplate used for calling a groupby reduction
    __device__ function in the case where the function is either
    `idxmax` or `idxmin`. See `lowering_function` for details. This
    lowering differs from other reductions due to the presence of
    the index. This results in the forward declaration expecting
    an extra arg.
    """
    retty = sig.return_type

    grp = cgutils.create_struct_proxy(sig.args[0])(
        context, builder, value=args[0]
    )
    grp_type = sig.args[0]

    if grp_type.index_type != index_default_type:
        raise TypeError(
            f"Only inputs with default index dtype {index_default_type} "
            "are supported."
        )

    group_dataty = grp_type.group_data_type
    group_data_ptr = builder.alloca(grp.group_data.type)
    builder.store(grp.group_data, group_data_ptr)

    index_dataty = grp_type.group_index_type
    index_ptr = builder.alloca(grp.index.type)
    builder.store(grp.index, index_ptr)
    type_key = (types.int64, grp_type.group_scalar_type)
    func = call_cuda_functions[function][type_key]

    return context.compile_internal(
        builder,
        func,
        nb_signature(retty, group_dataty, index_dataty, grp_type.size_type),
        (builder.load(group_data_ptr), builder.load(index_ptr), grp.size),
    )


cuda_Group_max = partial(lowering_function, function="max")
cuda_Group_min = partial(lowering_function, function="min")
cuda_Group_sum = partial(lowering_function, function="sum")
cuda_Group_mean = partial(lowering_function, function="mean")
cuda_Group_std = partial(lowering_function, function="std")
cuda_Group_var = partial(lowering_function, function="var")

cuda_Group_idxmax = partial(cuda_Group_idx_max_or_min, function="idxmax")
cuda_Group_idxmin = partial(cuda_Group_idx_max_or_min, function="idxmin")


def cuda_Group_size(context, builder, sig, args):
    grp = cgutils.create_struct_proxy(sig.args[0])(
        context, builder, value=args[0]
    )
    return grp.size


def cuda_Group_count(context, builder, sig, args):
    grp = cgutils.create_struct_proxy(sig.args[0])(
        context, builder, value=args[0]
    )
    return grp.size


for ty in SUPPORTED_GROUPBY_NUMBA_TYPES:
    cuda_lower("GroupType.max", GroupType(ty))(cuda_Group_max)
    cuda_lower("GroupType.min", GroupType(ty))(cuda_Group_min)
    cuda_lower("GroupType.sum", GroupType(ty))(cuda_Group_sum)
    cuda_lower("GroupType.count", GroupType(ty))(cuda_Group_count)
    cuda_lower("GroupType.size", GroupType(ty))(cuda_Group_size)
    cuda_lower("GroupType.mean", GroupType(ty))(cuda_Group_mean)
    cuda_lower("GroupType.std", GroupType(ty))(cuda_Group_std)
    cuda_lower("GroupType.var", GroupType(ty))(cuda_Group_var)
    cuda_lower("GroupType.idxmax", GroupType(ty, types.int64))(
        cuda_Group_idxmax
    )
    cuda_lower("GroupType.idxmin", GroupType(ty, types.int64))(
        cuda_Group_idxmin
    )
