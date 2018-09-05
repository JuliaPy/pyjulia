"""
(Maybe) Re-build PyCall.jl to test ``exe_differs=False`` path.

``Pkg.build("PyCall")`` is run on Julia side when the environment
variable `PYJULIA_TEST_REBUILD` is set to ``yes``.
"""

from __future__ import print_function, absolute_import

import os
import signal
import subprocess
import sys
from contextlib import contextmanager

from .core import juliainfo


@contextmanager
def maybe_rebuild(rebuild, julia):
    if rebuild:
        env = os.environ.copy()
        info = juliainfo(julia)

        build = [julia, '-e', """
        if VERSION >= v"0.7.0-DEV.3630"
            using Pkg
        end
        Pkg.build("PyCall")
        if VERSION < v"0.7.0"
            pkgdir = Pkg.dir("PyCall")
        else
            modpath = Base.locate_package(Base.identify_package("PyCall"))
            pkgdir = joinpath(dirname(modpath), "..")
        end
        logfile = joinpath(pkgdir, "deps", "build.log")
        if isfile(logfile)
            print(read(logfile, String))
        end
        """]
        print('Building PyCall.jl with PYTHON =', sys.executable)
        print(*build)
        sys.stdout.flush()
        subprocess.check_call(build, env=dict(env, PYTHON=sys.executable))
        try:
            yield
        finally:
            print()  # clear out messages from py.test
            print('Restoring previous PyCall.jl build...')
            print(*build)
            if info.pyprogramname:
                # Use str to avoid "TypeError: environment can only
                # contain strings" in Python 2.7 + Windows:
                env = dict(env, PYTHON=str(info.pyprogramname))
            if 'PYTHON' in env:
                print('PYTHON =', env['PYTHON'])
            subprocess.check_call(build, env=env)
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
        '--julia', default=os.getenv('JULIA_EXE', 'julia'),
        help="""
        Julia executable to be used.
        Default to the value of environment variable JULIA_EXE if set.
        """)
    parser.add_argument(
        'command', nargs='+',
        help='Command and arguments to run.')
    ns = parser.parse_args(args)
    ns.rebuild = ns.rebuild == 'yes'
    sys.exit(with_rebuilt(**vars(ns)))


if __name__ == '__main__':
    main()
