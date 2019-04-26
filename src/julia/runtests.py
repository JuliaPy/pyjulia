"""
Run tests for PyJulia.
"""

from __future__ import absolute_import, print_function

import argparse
import sys

from .utils import execprog

try:
    from shlex import quote
except ImportError:
    from pipes import quote  # Python 2.7


class ApplicationError(RuntimeError):
    pass


required_pytest = (3, 9)
"""
Required pytest version.

This is a very loose lower bound because we abort `runtests` CLI if
this does not match.
"""

msg_test_dependencies = """
Test dependencies are not installed.

To run `julia.runtests`, use the following command to install `pytest`:
    {} -m pip install "julia[test]"

Note that you may need to add option `--user` after `install`.
""".format(
    quote(sys.executable)
).strip()


def check_test_dependencies():
    # See `extras_require` in setup.py
    try:
        import numpy
        import IPython.testing.tools  # may require `mock`
    except ImportError as err:
        print(err, file=sys.stderr)
        raise ApplicationError(msg_test_dependencies)

    try:
        import pytest
    except ImportError as err:
        print(err, file=sys.stderr)
        raise ApplicationError(msg_test_dependencies)

    major, minor, _ = pytest.__version__.split(".", 2)
    if (int(major), int(minor)) < required_pytest:
        raise ApplicationError(msg_test_dependencies)


def runtests(pytest_args, dry_run):
    check_test_dependencies()

    # TODO: Detect segfault and report.
    # TODO: Maybe integrate this script with `with_rebuilt`?
    cmd = [
        sys.executable,
        "-m",
        "julia.with_rebuilt",
        "--",
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "pytester",
        "-p",
        "julia.pytestplugin",
        "--doctest-modules",
        "--runpytest=subprocess",
        "--pyargs",
        "julia",
    ]
    cmd.extend(pytest_args)
    if dry_run:
        print(*map(quote, cmd))
        return
    execprog(cmd)


class CustomFormatter(
    argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter
):
    pass


def main(args=None):
    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter, description=__doc__
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="""
        Print the command to be executed instead of actually running
        it.
        """,
    )
    parser.add_argument(
        "pytest_args",
        nargs="*",
        help="""
        Command line arguments to be passed to pytest.
        """,
    )
    ns, pytest_args = parser.parse_known_args(args)
    if ns.pytest_args and pytest_args:
        parser.error(
            "Ambiguous arguments.  Use `--` to separate pytest options"
            " from options for julia.runtests."
        )
    if pytest_args:
        ns.pytest_args = pytest_args
    try:
        runtests(**vars(ns))
    except ApplicationError as err:
        print(err, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
