"""
Build system image.

Example::

    python3 -m julia.sysimage sys.so

Generated system image can be passed to ``sysimage`` option of
`julia.api.Julia`.

.. note::

   This script is not tested on Windows.
"""

from __future__ import absolute_import, print_function

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from logging import getLogger  # see `.core.logger`

from .core import enable_debug
from .tools import julia_py_executable

logger = getLogger("julia.sysimage")


class KnownError(RuntimeError):
    pass


def script_path(name):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), name)


def install_packagecompiler_cmd(julia, compiler_env):
    cmd = [julia]
    if sys.stdout.isatty():
        cmd.append("--color=yes")
    cmd.append(script_path("install-packagecompiler.jl"))
    cmd.append(compiler_env)
    return cmd


def build_sysimage_cmd(julia_py, julia, compile_args):
    cmd = [julia_py, "--julia", julia]
    if sys.stdout.isatty():
        cmd.append("--color=yes")
    cmd.append(script_path("compile.jl"))
    cmd.extend(compile_args)
    return cmd


def check_call(cmd, **kwargs):
    logger.debug("Run %s", cmd)
    subprocess.check_call(cmd, **kwargs)


@contextmanager
def temporarydirectory(**kwargs):
    path = tempfile.mkdtemp(**kwargs)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def build_sysimage(
    output,
    julia="julia",
    script=script_path("precompile.jl"),
    debug=False,
    compiler_env="",
):
    if debug:
        enable_debug()

    if output.endswith(".a"):
        raise KnownError("Output file must not have extension .a")

    julia_py = julia_py_executable()

    with temporarydirectory(prefix="tmp.pyjulia.sysimage.") as path:
        if not compiler_env:
            compiler_env = os.path.join(path, "compiler_env")
            # Not using julia-py to install PackageCompiler to reduce
            # method re-definition warnings:
            check_call(install_packagecompiler_cmd(julia, compiler_env), cwd=path)

        # Arguments to ./compile.jl script:
        compile_args = [
            compiler_env,
            # script -- ./precompile.jl by default
            os.path.realpath(script),
            # output -- path to sys.o file
            os.path.realpath(output),
        ]

        check_call(build_sysimage_cmd(julia_py, julia, compile_args), cwd=path)


class CustomFormatter(
    argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter
):
    pass


def main(args=None):
    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter, description=__doc__
    )
    parser.add_argument("--julia", default="julia")
    parser.add_argument("--debug", action="store_true", help="Print debug log.")
    parser.add_argument(
        "--script",
        default=script_path("precompile.jl"),
        help="Path to Julia script with precopmile instructions.",
    )
    parser.add_argument(
        "--compiler-env",
        default="",
        help="""
        Path to a Julia project with PackageCompiler to be used for
        system image compilation.  Create a temporary environment with
        appropriate PackageCompiler by default or when an empty string
        is given.
        """,
    )
    parser.add_argument("output", help="Path to system image file sys.o.")
    ns = parser.parse_args(args)
    try:
        build_sysimage(**vars(ns))
    except (KnownError, subprocess.CalledProcessError) as err:
        print(err, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
