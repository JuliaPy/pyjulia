"""
(Maybe) Re-build PyCall.jl to test ``exe_differs=False`` path.

``Pkg.build("PyCall")`` is run on Julia side when the environment
variable `PYJULIA_TEST_REBUILD` is set to ``yes``.
"""

from __future__ import absolute_import, print_function

import os
import signal
import subprocess
import sys
from contextlib import contextmanager

from .core import JuliaInfo
from .tools import build_pycall

# fmt: off


@contextmanager
def maybe_rebuild(rebuild, julia):
    if rebuild:
        info = JuliaInfo.load(julia)

        print('Building PyCall.jl with PYTHON =', sys.executable)
        sys.stdout.flush()
        build_pycall(julia=julia, python=sys.executable)
        try:
            yield
        finally:
            if info.python:
                # Use str to avoid "TypeError: environment can only
                # contain strings" in Python 2.7 + Windows:
                python = str(info.python)
                print()  # clear out messages from py.test
                print('Restoring previous PyCall.jl build with PYTHON =', python)
                build_pycall(julia=julia, python=python, quiet=True)
    else:
        yield


@contextmanager
def ignoring(sig):
    """
    Context manager for ignoring signal `sig`.

    For example,::

        with ignoring(signal.SIGINT):
            do_something()

    would ignore user's ctrl-c during ``do_something()``.  This is
    useful when launching interactive program (in which ctrl-c is a
    valid keybinding) from Python.
    """
    s = signal.signal(sig, signal.SIG_IGN)
    try:
        yield
    finally:
        signal.signal(sig, s)


def with_rebuilt(rebuild, julia, command):
    with maybe_rebuild(rebuild, julia), ignoring(signal.SIGINT):
        print('Execute:', *command)
        return subprocess.call(command)


def main(args=None):
    import argparse
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=__doc__)
    parser.add_argument(
        '--rebuild', default=os.getenv('PYJULIA_TEST_REBUILD', 'no'),
        choices=('yes', 'no'),
        help="""
        *Be careful using this option!* When it is set to `yes`, your
        `PyCall.jl` installation will be rebuilt using the Python
        interpreter used for testing.  The test suite tries to build
        back to the original configuration but the precompilation
        would be in the stale state after the test.  Note also that it
        does not work if you unconditionally set `PYTHON` environment
        variable in your Julia startup file.
        """)
    parser.add_argument(
        '--julia', default=os.getenv('PYJULIA_TEST_RUNTIME', 'julia'),
        help="""
        Julia executable to be used.
        Default to the value of environment variable PYJULIA_TEST_RUNTIME if set.
        """)
    parser.add_argument(
        'command', nargs='+',
        help='Command and arguments to run.')
    ns = parser.parse_args(args)
    ns.rebuild = ns.rebuild == 'yes'
    sys.exit(with_rebuilt(**vars(ns)))


if __name__ == '__main__':
    main()
