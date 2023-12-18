# """cache.py"""
from collections import OrderedDict
from inspect import signature, Signature
from typing import Any, Callable, Dict, List

from fastapi import Request, Response

from .types import ArgType, SigParameters

ALWAYS_IGNORE_ARG_TYPES = [Response, Request]


def get_cache_key(
    prefix: str,
    ignore_arg_types: List[ArgType],
    func: Callable,
    *args: List,
    **kwargs: Dict,
) -> str:
    """Generate a unique identifier for the function and its arguments, suitable for use as a cache key."""
    ignore_arg_types = list(set(ignore_arg_types or []) | set(ALWAYS_IGNORE_ARG_TYPES))
    prefix = f"{prefix}:" if prefix else ""

    sig = signature(func)
    func_args = get_func_args(sig, *args, **kwargs)
    args_str = get_args_str(sig.parameters, func_args, ignore_arg_types)

    return f"{prefix}{func.__module__}.{func.__name__}({args_str})"


def get_func_args(
    sig: Signature, *args: List, **kwargs: Dict
) -> "OrderedDict[str, Any]":
    """Return a dictionary containing the names and values of all function arguments."""
    func_args = sig.bind(*args, **kwargs)
    func_args.apply_defaults()
    return func_args.arguments


def get_args_str(
    sig_params: SigParameters,
    func_args: "OrderedDict[str, Any]",
    ignore_arg_types: List[ArgType],
) -> str:
    """Return a string representation of the arguments and their values."""
    valid_args = (
        f"{arg}={val}"
        for arg, val in func_args.items()
        if sig_params[arg].annotation not in ignore_arg_types
    )
    return ",".join(valid_args)
