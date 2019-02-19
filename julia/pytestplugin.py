from __future__ import print_function, absolute_import

import pytest


def pytest_addoption(parser):
    import os

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


@pytest.fixture(scope="session")
def julia(request):
    """ pytest fixture for providing a `Julia` instance. """
    if not request.config.getoption("julia"):
        pytest.skip("--no-julia is given.")

    from julia.core import Julia

    jl = Julia(runtime=request.config.getoption("julia_runtime"), debug=True)
    return jl
