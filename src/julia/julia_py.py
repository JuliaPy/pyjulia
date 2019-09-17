"""
Launch Julia through PyJulia.

Currently, `julia-py` is primary used internally for supporting
`julia.sysimage` command line interface.  Using `julia-py` like normal
Julia program requires `--sysimage` to be set to the system image
created by `julia.sysimage`.

Example::

    $ python3 -m julia.sysimage sys.so
    $ julia-py --sysimage sys.so
"""

from __future__ import absolute_import, print_function

import argparse
import os
import sys

from .api import LibJulia
from .core import enable_debug, which
from .tools import julia_py_executable


def julia_py(julia, pyjulia_debug, jl_args):
    if pyjulia_debug:
        enable_debug()

    julia = which(julia)
    os.environ["_PYJULIA_JULIA"] = julia
    os.environ["_PYJULIA_JULIA_PY"] = julia_py_executable()
    os.environ["_PYJULIA_PATCH_JL"] = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "patch.jl"
    )

    api = LibJulia.load(julia=julia)
    api.init_julia(jl_args)
    code = 1
    if not api.jl_eval_string(b"Base.PCRE.__init__()"):
        print("julia-py: Error while calling `Base.PCRE.__init__()`", file=sys.stderr)
        sys.exit(code)
    if api.jl_eval_string(b"""Base.include(Main, ENV["_PYJULIA_PATCH_JL"])"""):
        if api.jl_eval_string(b"Base.invokelatest(Base._start)"):
            code = 0
    api.jl_atexit_hook(code)
    sys.exit(code)


class CustomFormatter(
    argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter
):
    pass


def parse_args(args, **kwargs):
    options = dict(
        prog="julia-py",
        usage="%(prog)s [--julia JULIA] [--pyjulia-debug] [<julia arguments>...]",
        formatter_class=CustomFormatter,
        description=__doc__,
    )
    options.update(kwargs)
    parser = argparse.ArgumentParser(**options)
    parser.add_argument(
        "--julia",
        default=os.environ.get("_PYJULIA_JULIA", "julia"),
        help="""
        Julia `executable` used by PyJulia.
        """,
    )
    parser.add_argument(
        "--pyjulia-debug",
        action="store_true",
        help="""
        Print PyJulia's debugging messages to standard error.
        """,
    )
    ns, jl_args = parser.parse_known_args(args)
    ns.jl_args = jl_args
    return ns


def main(args=None, **kwargs):
    julia_py(**vars(parse_args(args, **kwargs)))


if __name__ == "__main__":
    main()
