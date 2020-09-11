from __future__ import absolute_import, print_function

import glob
import os
import re
import subprocess
import sys
import sysconfig

from .core import JuliaNotFound, which
from .find_libpython import linked_libpython


class PyCallInstallError(RuntimeError):
    def __init__(self, op, output=None):
        self.op = op
        self.output = output

    def __str__(self):
        if self.output:
            return "{} PyCall failed with output:\n\n{}".format(self.op, self.output)
        else:
            return """\
{} PyCall failed.

** Important information from Julia may be printed before Python's Traceback **

Some useful information may also be stored in the build log file
`~/.julia/packages/PyCall/*/deps/build.log`.
""".format(
                self.op
            )


def _julia_version(julia):
    output = subprocess.check_output([julia, "--version"], universal_newlines=True)
    match = re.search(r"([0-9]+)\.([0-9]+)\.([0-9]+)", output)
    if match:
        return tuple(int(match.group(i + 1)) for i in range(3))
    else:
        return (0, 0, 0)


def _non_default_julia_warning_message(julia):
    # Avoid confusion like
    # https://github.com/JuliaPy/pyjulia/issues/416
    return (
        "PyCall is setup for non-default Julia runtime (executable) `{julia}`.\n"
        "To use this Julia runtime, PyJulia has to be initialized first by\n"
        "    from julia import Julia\n"
        "    Julia(runtime={julia!r})"
    ).format(julia=julia)


def build_pycall(julia="julia", python=sys.executable, **kwargs):
    # Passing `python` to force build (OP="build")
    install(julia=julia, python=python, **kwargs)


def install(julia="julia", color="auto", python=None, quiet=False):
    """
    install(*, julia="julia", color="auto")
    Install Julia packages required by PyJulia in `julia`.

    This function installs and/or re-builds PyCall if necessary.  It
    also makes sure to build PyCall in a way compatible with this
    Python executable (if possible).

    Keyword Arguments
    -----------------
    julia : str
        Julia executable (default: "julia")
    color : "auto", False or True
        Use colorful output if `True`.  "auto" (default) to detect it
        automatically.
    """
    if which(julia) is None:
        raise JuliaNotFound(julia, kwargname="julia")

    libpython = linked_libpython() or ""

    julia_cmd = [julia, "--startup-file=no"]
    if quiet:
        color = False
    if color == "auto":
        color = sys.stdout.isatty()
    if color:
        # `--color=auto` doesn't work?
        julia_cmd.append("--color=yes")
        """
        if _julia_version(julia) >= (1, 1):
            julia_cmd.append("--color=auto")
        else:
            julia_cmd.append("--color=yes")
        """

    OP = "build" if python else "install"
    install_cmd = julia_cmd + [
        os.path.join(os.path.dirname(os.path.realpath(__file__)), "install.jl"),
        "--",
        OP,
        python or sys.executable,
        libpython,
    ]

    kwargs = {}
    if quiet:
        kwargs.update(
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True
        )
    proc = subprocess.Popen(install_cmd, **kwargs)
    output, _ = proc.communicate()
    returncode = proc.returncode

    if returncode == 113:  # code_no_precompile_needed
        return
    elif returncode != 0:
        raise PyCallInstallError("Installing", output)

    if not quiet:
        print(file=sys.stderr)
        print("Precompiling PyCall...", file=sys.stderr)
        sys.stderr.flush()
    precompile_cmd = julia_cmd + ["-e", "using PyCall"]
    returncode = subprocess.call(precompile_cmd)
    if returncode != 0:
        raise PyCallInstallError("Precompiling")
    if not quiet:
        print("Precompiling PyCall... DONE", file=sys.stderr)
        print("PyCall is installed and built successfully.", file=sys.stderr)
        if julia != "julia":
            print(file=sys.stderr)
            print(_non_default_julia_warning_message(julia), file=sys.stderr)
        sys.stderr.flush()


def make_receiver(io):
    def receiver(s):
        io.write(s)
        io.flush()

    return receiver


def redirect_output_streams():
    """
    Redirect Julia's stdout and stderr to Python's counter parts.
    """

    from .Main._PyJuliaHelper.IOPiper import pipe_std_outputs

    pipe_std_outputs(make_receiver(sys.stdout), make_receiver(sys.stderr))

    # TODO: Invoking `redirect_output_streams()` in terminal IPython
    # terminates the whole Python process.  Find out why.


def julia_py_executable():
    """
    Path to ``julia-py`` executable installed for this Python executable.
    """

    # try to find installed julia-py script - check scripts folders under different installation schemes
    # we check the alternate schemes first, at most one of which should give us a julia-py script
    # if no candidate in an alternate scheme, try the standard install location
    # see https://docs.python.org/3/install/index.html#alternate-installation
    scripts_paths = [
        sysconfig.get_path("scripts", scheme) for scheme in sysconfig.get_scheme_names()
    ]
    scripts_paths.append(sysconfig.get_path("scripts"))

    for scripts_path in scripts_paths:
        stempath = os.path.join(scripts_path, "julia-py")
        candidates = {os.path.basename(p): p for p in glob.glob(stempath + "*")}
        if candidates:
            break

    if not candidates:
        raise RuntimeError(
            "``julia-py`` executable is not found for Python installed at {}".format(
                scripts_paths
            )
        )

    for basename in ["julia-py", "julia-py.exe", "julia-py.cmd"]:
        try:
            return candidates[basename]
        except KeyError:
            continue

    raise RuntimeError(
        """\
``julia-py`` with following unrecognized extension(s) are found.
Please report it at https://github.com/JuliaPy/pyjulia/issues
with the full traceback.
Files found:
    """
        + "    \n".join(sorted(candidates))
    )
