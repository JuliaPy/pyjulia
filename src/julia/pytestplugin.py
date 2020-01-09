from __future__ import absolute_import, print_function

import sys

import pytest

from .options import JuliaOptions

_USING_DEFAULT_SETUP = True


def pytest_addoption(parser):
    import os

    # Note: the help strings have to be synchronized manually with
    # ../../docs/source/pytest.rst

    parser.addoption(
        "--no-julia",
        action="store_false",
        dest="julia",
        default=True,
        help="Skip tests that require julia.",
    )
    parser.addoption(
        "--julia",
        action="store_true",
        dest="julia",
        default=True,
        help="Undo `--no-julia`; i.e., run tests that require julia.",
    )
    parser.addoption(
        "--julia-runtime",
        help="""
        Julia executable to be used.  Defaults to environment variable
        `$PYJULIA_TEST_RUNTIME`.
        """,
        default=os.getenv("PYJULIA_TEST_RUNTIME", "julia"),
    )

    for desc in JuliaOptions.supported_options():
        parser.addoption(
            "--julia-{}".format(desc.cli_argument_name().lstrip("-")),
            **desc.cli_argument_spec()
        )


def pytest_sessionstart(session):
    from .core import LibJulia, JuliaInfo, Julia, enable_debug

    options = JuliaOptions()
    for desc in JuliaOptions.supported_options():
        cli_option = "--julia-{}".format(desc.cli_argument_name().lstrip("-"))
        desc.__set__(options, session.config.getoption(cli_option))

    julia_runtime = session.config.getoption("julia_runtime")

    global _USING_DEFAULT_SETUP
    _USING_DEFAULT_SETUP = not (julia_runtime != "julia" or options.as_args())

    if not session.config.getoption("julia"):
        return

    enable_debug()
    global _JULIA_INFO
    _JULIA_INFO = info = JuliaInfo.load(julia=julia_runtime)

    if not info.is_pycall_built():
        print(
            """
PyCall is not installed or built.  Run the following code in Python REPL:

    >>> import julia
    >>> julia.install()

See:
    https://pyjulia.readthedocs.io/en/latest/installation.html
            """,
            file=sys.stderr,
        )
        pytest.exit("PyCall not built", returncode=1)

    if (
        options.compiled_modules != "no"
        and not info.is_compatible_python()
        and info.version_info >= (0, 7)
    ):
        print(
            """
PyJulia does not fully support this combination of Julia and Python.
Try:

    * Pass `--julia-compiled-modules=no` option to disable
      precompilation cache.

    * Use `--julia-runtime` option to specify different Julia
      executable.

    * Pass `--no-julia` to run tests that do not rely on Julia
      runtime.
            """,
            file=sys.stderr,
        )
        pytest.exit("incompatible runtimes", returncode=1)

    api = LibJulia.from_juliainfo(info)
    api.init_julia(options)


# Initialize Julia runtime as soon as possible (or more precisely
# before importing any additional Python modules) to avoid, e.g.,
# incompatibility of `libstdc++`.
#
# See:
# https://docs.pytest.org/en/latest/reference.html#_pytest.hookspec.pytest_sessionstart


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "julia: mark tests to be skipped with --no-julia."
    )
    # https://docs.pytest.org/en/latest/writing_plugins.html#registering-markers
    # https://docs.pytest.org/en/latest/mark.html#registering-marks


@pytest.fixture(scope="session")
def julia(request):
    """ pytest fixture for providing a `Julia` instance. """
    if not request.config.getoption("julia"):
        pytest.skip("--no-julia is given.")

    from .core import Julia

    return Julia()


@pytest.fixture(scope="session")
def juliainfo(julia):
    """ pytest fixture for providing `JuliaInfo` instance. """
    return _JULIA_INFO


def pytest_runtest_setup(item):
    if not item.config.getoption("julia"):
        for mark in item.iter_markers("julia"):
            pytest.skip("--no-julia is given.")

    if not _USING_DEFAULT_SETUP:
        for mark in item.iter_markers("pyjulia__using_default_setup"):
            pytest.skip(
                "using non-default setup (e.g., --julia-<julia_option> is given)"
            )
