from __future__ import print_function, absolute_import

from argparse import Namespace
import os
import sys

from .api import LibJulia
from .tools import julia_py_executable


def parse_args(args):
    ns = Namespace(julia="julia")
    jl_args = list(args)

    if len(jl_args) >= 2 and jl_args[0] == "--julia":
        ns.julia = jl_args[1]
        jl_args = jl_args[2:]
    elif len(jl_args) >= 1 and jl_args[0].startswith("--julia="):
        ns.julia = jl_args[0][len("--julia=") :]
        jl_args = jl_args[1:]

    return ns, jl_args


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    ns, jl_args = parse_args(args)

    os.environ["_PYJULIA_JULIA_PY"] = julia_py_executable()
    os.environ["_PYJULIA_PATCH_JL"] = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "patch.jl"
    )

    api = LibJulia.load(julia=ns.julia)
    api.init_julia(jl_args)
    code = 1
    if api.jl_eval_string(b"""Base.include(Main, ENV["_PYJULIA_PATCH_JL"])"""):
        if api.jl_eval_string(b"Base.invokelatest(Base._start)"):
            code = 0
    api.jl_atexit_hook(code)
    sys.exit(code)


if __name__ == "__main__":
    main()
