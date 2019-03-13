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


def pytest_sessionstart(session):
    if not session.config.getoption("julia"):
        return

    from .core import enable_debug, Julia, LibJulia, JuliaInfo

    enable_debug()
    info = JuliaInfo.load(julia=session.config.getoption("julia_runtime"))
    api = LibJulia.from_juliainfo(info)
    if info.is_compatible_python() or info.version_info < (0, 7):
        api.init_julia()
    else:
        api.init_julia(["--compiled-modules=no"])

    global JULIA
    JULIA = Julia()

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

    return JULIA
