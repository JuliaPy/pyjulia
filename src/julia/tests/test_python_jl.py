import os
import shlex
import subprocess
from textwrap import dedent

import pytest

from julia.core import which
from julia.python_jl import parse_pyjl_args

PYJULIA_TEST_REBUILD = os.environ.get("PYJULIA_TEST_REBUILD", "no") == "yes"

python_jl_required = pytest.mark.skipif(
    os.environ.get("PYJULIA_TEST_PYTHON_JL_IS_INSTALLED", "no") != "yes"
    and not which("python-jl"),
    reason="python-jl command not found",
)

# fmt: off


@pytest.mark.parametrize("args", [
    "-h",
    "-i --help",
    "--julia false -h",
    "--julia false -i --help",
])
def test_help_option(args, capsys):
    with pytest.raises(SystemExit) as exc_info:
        parse_pyjl_args(shlex.split(args))
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "usage:" in captured.out


quick_pass_cli_args = [
    "-h",
    "-i --help",
    "-V",
    "--version -c 1/0",
]


@python_jl_required
@pytest.mark.parametrize("args", quick_pass_cli_args)
def test_cli_quick_pass(args):
    subprocess.check_output(
        ["python-jl"] + shlex.split(args),
    )


@python_jl_required
@pytest.mark.skipif(
    not which("false"),
    reason="false command not found")
@pytest.mark.parametrize("args", quick_pass_cli_args)
def test_cli_quick_pass_no_julia(args):
    subprocess.check_output(
        ["python-jl", "--julia", "false"] + shlex.split(args),
    )


@python_jl_required
@pytest.mark.skipif(
    # This test makes sense only when PyJulia is importable by
    # `PyCall.python`.  Thus, it is safe to run this test only when
    # `PYJULIA_TEST_REBUILD=yes`; i.e., PyCall is using this Python
    # executable.
    not PYJULIA_TEST_REBUILD,
    reason="PYJULIA_TEST_REBUILD=yes is not set")
def test_cli_import(juliainfo):
    code = """
    from julia import Base
    Base.banner()
    from julia import Main
    Main.x = 1
    assert Main.x == 1
    """
    args = ["--julia", juliainfo.julia, "-c", dedent(code)]
    output = subprocess.check_output(
        ["python-jl"] + args,
        universal_newlines=True)
    assert "julialang.org" in output

# Embedded julia does not have usual the Main.eval and Main.include.
# Main.eval is Core.eval.  Let's test that we are not relying on this
# special behavior.
#
# See also: https://github.com/JuliaLang/julia/issues/28825
