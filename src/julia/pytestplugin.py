from __future__ import print_function, absolute_import

import pytest

from .options import JuliaOptions


def pytest_addoption(parser):
    import os

    # Note: the help strings have to be synchronized manually with
    # ../../docs/source/pytest.rst

    parser.addoption(
        "--no-julia",
        action="store_false",
        dest="julia",
        help="Skip tests that require julia.",
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
    if not session.config.getoption("julia"):
        return

    from .core import LibJulia, enable_debug

    options = JuliaOptions()
    for desc in JuliaOptions.supported_options():
        cli_option = "--julia-{}".format(desc.cli_argument_name().lstrip("-"))
        desc.__set__(options, session.config.getoption(cli_option))

    enable_debug()
    api = LibJulia.load(julia=session.config.getoption("julia_runtime"))
    api.init_julia(options)


# Initialize Julia runtime as soon as possible (or more precisely
# before importing any additional Python modules) to avoid, e.g.,
# incompatibility of `libstdc++`.
#
# See:
# https://docs.pytest.org/en/latest/reference.html#_pytest.hookspec.pytest_sessionstart


@pytest.fixture(scope="session")
def julia(request):
    """ pytest fixture for providing a `Julia` instance. """
    if not request.config.getoption("julia"):
        pytest.skip("--no-julia is given.")

    from .core import Julia

    return Julia()
