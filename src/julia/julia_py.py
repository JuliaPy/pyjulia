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
from logging import getLogger  # see `.core.logger`

from .api import JuliaInfo, LibJulia
from .core import enable_debug, which
from .tools import julia_py_executable

logger = getLogger("julia")


def julia_py(julia, pyjulia_debug, jl_args):
    pyjulia_debug = True
    if pyjulia_debug:
        enable_debug()

    julia = which(julia)
    os.environ["_PYJULIA_JULIA"] = julia
    os.environ["_PYJULIA_JULIA_PY"] = julia_py_executable()
    os.environ["_PYJULIA_PATCH_JL"] = patch_jl_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "patch.jl"
    )

    juliainfo = JuliaInfo.load(julia=julia)
    api = LibJulia.from_juliainfo(juliainfo)
    api.init_julia(jl_args)
    code = 1
    if True:
        logger.debug("Skipping `__init__()` hacks in `julia` %s", juliainfo.version_raw)
    else:
        logger.debug("Calling `Base.PCRE.__init__()`")
        if not api.jl_eval_string(b"Base.PCRE.__init__()"):
            print(
                "julia-py: Error while calling `Base.PCRE.__init__()`", file=sys.stderr
            )
            sys.exit(code)
        logger.debug("Calling `Random.__init__()`")
        if not api.jl_eval_string(
            b"""
            Base.require(
                Base.PkgId(
                    Base.UUID("9a3f8284-a2c9-5f02-9a11-845980a1fd5c"),
                    "Random",
                ),
            ).__init__()
            """
        ):
            print("julia-py: Error while calling `Random.__init__()`", file=sys.stderr)
            sys.exit(code)
    logger.debug("Loading %s", patch_jl_path)
    if not api.jl_eval_string(b"""Base.include(Main, ENV["_PYJULIA_PATCH_JL"])"""):
        print("julia-py: Error in", patch_jl_path, file=sys.stderr)
        sys.exit(code)
    logger.debug("Calling `Base._start()`")
    if api.jl_eval_string(b"Base.invokelatest(Base._start)"):
        code = 0
    logger.debug("Calling `jl_atexit_hook(%s)`", code)
    api.jl_atexit_hook(code)
    logger.debug("Exiting with code %s", code)
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
