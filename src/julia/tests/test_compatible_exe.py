from __future__ import print_function

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from contextlib import contextmanager

import pytest

import julia
from julia.core import which

is_linux = sys.platform.startswith("linux")
is_windows = os.name == "nt"
is_apple = sys.platform == "darwin"


def _get_paths(path):
    return list(filter(None, path.split(":")))


# Environment variable PYJULIA_TEST_INCOMPATIBLE_PYTHONS is the
# :-separated list of Python executables incompatible with the current
# Python:
incompatible_pythons = _get_paths(os.getenv("PYJULIA_TEST_INCOMPATIBLE_PYTHONS", ""))


try:
    from types import SimpleNamespace
except ImportError:
    # Python 2:
    from argparse import Namespace as SimpleNamespace


def _run_fallback(args, input=None, **kwargs):
    # A port of subprocess.run just enough to run the tests.
    process = subprocess.Popen(args, stdin=subprocess.PIPE, **kwargs)
    stdout, stderr = process.communicate(input)
    retcode = process.wait()
    return SimpleNamespace(args=args, stdout=stdout, stderr=stderr, returncode=retcode)


try:
    from subprocess import run
except ImportError:
    run = _run_fallback


@contextmanager
def tmpdir_if(should):
    if should:
        path = tempfile.mkdtemp(prefix="tmp-pyjulia-test")
        try:
            yield path
        finally:
            shutil.rmtree(path, ignore_errors=True)
    else:
        yield None


def runcode(code, python=None, check=False, env=None, **kwargs):
    """Run `code` in `python`."""
    env = (env or os.environ).copy()

    with tmpdir_if(python) as path:
        if path is not None:
            # Make PyJulia importable.
            shutil.copytree(
                os.path.dirname(os.path.realpath(julia.__file__)),
                os.path.join(path, "julia"),
            )
            env["PYTHONPATH"] = path
        proc = run(
            [python or sys.executable],
            input=textwrap.dedent(code),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            env=env,
            **kwargs
        )
    print_completed_proc(proc)
    if check:
        assert proc.returncode == 0
    return proc


def print_completed_proc(proc):
    # Print output (pytest will hide it by default):
    print("Ran:", *proc.args)
    if proc.stdout:
        print("# --- STDOUT from", *proc.args)
        print(proc.stdout)
    if proc.stderr:
        print("# --- STDERR from", *proc.args)
        print(proc.stderr)
    print("# ---")


def is_dynamically_linked(executable):
    """
    Check if Python `executable` is (likely to be) dynamically linked.

    It returns three possible values:

    * `True`: Likely that it's dynamically linked.
    * `False`: Likely that it's statically linked.
    * `None`: Unsupported platform.

    It's only "likely" since the check is by simple occurrence of a
    some substrings like "libpython".  For example, if there is
    another library existing on the path containing "libpython", this
    function may return false-positive.
    """
    path = which(executable)
    assert os.path.exists(path)
    if is_linux and which("ldd"):
        proc = run(["ldd", path], stdout=subprocess.PIPE, universal_newlines=True)
        print_completed_proc(proc)
        return "libpython" in proc.stdout
    elif is_apple and which("otool"):
        proc = run(
            ["otool", "-L", path], stdout=subprocess.PIPE, universal_newlines=True
        )
        print_completed_proc(proc)
        return (
            "libpython" in proc.stdout
            or "/Python" in proc.stdout
            or "/.Python" in proc.stdout
        )
    # TODO: support Windows
    return None


@pytest.mark.parametrize("python", incompatible_pythons)
def test_incompatible_python(python, julia):
    python = which(python)
    proc = runcode(
        """
        import os
        from julia import Julia
        Julia(runtime=os.getenv("PYJULIA_TEST_RUNTIME"), debug=True)
        """,
        python,
    )

    assert proc.returncode == 1
    assert "It seems your Julia and PyJulia setup are not supported." in proc.stderr
    dynamic = is_dynamically_linked(python)
    if dynamic is True:
        assert "`libpython` have to match" in proc.stderr
    elif dynamic is False:
        assert "is statically linked to libpython" in proc.stderr


@pytest.mark.parametrize(
    "python",
    [
        p
        for p in filter(None, map(which, incompatible_pythons))
        if is_dynamically_linked(p) is False
    ],
)
def test_statically_linked(python):
    """
    Simulate the case PyCall is configured with statically linked Python.

    In this case, `find_libpython()` would return the path identical
    to the one in PyCall's deps.jl.  `is_compatible_exe` should reject
    it.
    """
    python = which(python)
    runcode(
        """
        from __future__ import print_function
        from julia.core import enable_debug
        from julia.find_libpython import find_libpython
        from julia.juliainfo import is_compatible_exe

        enable_debug()
        assert not is_compatible_exe(find_libpython())
        """,
        python,
        check=True,
    )
