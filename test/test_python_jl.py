from textwrap import dedent
import os
import subprocess

import pytest

from julia.core import which
from julia.python_jl import parse_pyjl_args

is_windows = os.name == "nt"

PYJULIA_TEST_REBUILD = os.environ.get("PYJULIA_TEST_REBUILD", "no") == "yes"
JULIA = os.environ.get("JULIA_EXE")


@pytest.mark.parametrize("cli_args", [
    ["-h"],
    ["-i", "--help"],
    ["--julia", "false", "-h"],
    ["--julia", "false", "-i", "--help"],
])
def test_help_option(cli_args, capsys):
    with pytest.raises(SystemExit) as exc_info:
        parse_pyjl_args(cli_args)
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "usage:" in captured.out


quick_pass_cli_args = [
    ["-h"],
    ["-i", "--help"],
    ["-V"],
    ["--version", "-c", "1/0"],
]


@pytest.mark.parametrize("cli_args", quick_pass_cli_args)
def test_cli_quick_pass(cli_args):
    subprocess.check_output(
        ["python-jl"] + cli_args,
    )


@pytest.mark.skipif(
    not which("false"),
    reason="false command not found")
@pytest.mark.parametrize("cli_args", quick_pass_cli_args)
def test_cli_quick_pass_no_julia(cli_args):
    subprocess.check_output(
        ["python-jl", "--julia", "false"] + cli_args,
    )


@pytest.mark.skipif(
    is_windows,
    reason="python-jl is not supported in Windows")
@pytest.mark.skipif(
    not PYJULIA_TEST_REBUILD,
    reason="PYJULIA_TEST_REBUILD=yes is not set")
def test_cli_import():
    cli_args = ["-c", dedent("""
    from julia import Base
    Base.banner()
    from julia import Main
    Main.x = 1
    assert Main.x == 1
    """)]
    if JULIA:
        cli_args = ["--julia", JULIA] + cli_args
    output = subprocess.check_output(
        ["python-jl"] + cli_args,
        universal_newlines=True)
    assert "julialang.org" in output

# Embedded julia does not have usual the Main.eval and Main.include.
# Main.eval is Core.eval.  Let's test that we are not relying on this
# special behavior.
#
# See also: https://github.com/JuliaLang/julia/issues/28825
