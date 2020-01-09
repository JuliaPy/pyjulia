import sys
from textwrap import dedent

import pytest
from IPython.testing import globalipapp

from julia import magic


@pytest.fixture
def julia_magics(julia):
    return magic.JuliaMagics(shell=globalipapp.get_ipython())


# fmt: off


@pytest.fixture
def run_cell(julia_magics):
    # a more convenient way to run strings (possibly with magic) as if they were
    # an IPython cell
    def run_cell_impl(cell):
        cell = dedent(cell).strip()
        if cell.startswith("%%"):
            return julia_magics.shell.run_cell_magic("julia","",cell.replace("%%julia","").strip())
        else:
            exec_result = julia_magics.shell.run_cell(cell)
            if exec_result.error_in_exec:
                raise exec_result.error_in_exec
            else:
                return exec_result.result
    return run_cell_impl


def test_register_magics(julia):
    magic.load_ipython_extension(globalipapp.get_ipython())


def test_success_line(julia_magics):
    ans = julia_magics.julia('1')
    assert ans == 1


def test_success_cell(julia_magics):
    ans = julia_magics.julia(None, '2')
    assert ans == 2


def test_failure_line(julia_magics):
    with pytest.raises(Exception):
        julia_magics.julia('pop!([])')


def test_failure_cell(julia_magics):
    with pytest.raises(Exception):
        julia_magics.julia(None, '1 += 1')


# In IPython, $x does a string interpolation handled by IPython itself for
# *line* magic, which prior to IPython 7.3 could not be turned off. However,
# even prior to IPython 7.3, *cell* magic never did the string interpolation, so
# below, any time we need to test $x interpolation, do it as cell magic so it
# works on IPython < 7.3

def test_interp_var(run_cell):
    run_cell("x=1")
    assert run_cell("""
    %%julia
    $x
    """) == 1
    
def test_interp_expr(run_cell):
    assert run_cell("""
    x=1
    %julia py"x+1"
    """) == 2

def test_bad_interp(run_cell):
    with pytest.raises(Exception):
        assert run_cell("""
        %%julia
        $(x+1)
        """)

def test_string_interp(run_cell):
    run_cell("foo='python'")
    assert run_cell("""
    %%julia 
    foo="julia"
    "$foo", "$($foo)"
    """) == ('julia','python')

def test_expr_interp(run_cell):
    run_cell("foo='python'")
    assert run_cell("""
    %%julia 
    foo="julia"
    :($foo), :($($foo))
    """) == ('julia','python')
    
def test_expr_py_interp(run_cell):
    assert "baz" in str(run_cell("""
    %julia :(py"baz")
    """))
    
def test_macro_esc(run_cell):
    assert run_cell("""
    %%julia
    x = 1
    @eval y = $x
    y
    """) == 1

def test_type_conversion(run_cell):
    assert run_cell("""
    %julia py"1" isa Integer && py"1"o isa PyObject
    """) == True

def test_local_scope(run_cell):
    assert run_cell("""
    x = "global"
    def f():
        x = "local"
        ret = %julia py"x"
        return ret
    f()
    """) == "local"
    
def test_global_scope(run_cell):
    assert run_cell("""
    x = "global"
    def f():
        ret = %julia py"x"
        return ret
    f()
    """) == "global"
    
def test_noretvalue(run_cell):
    assert run_cell("""
    %%julia
    1+2;
    """) is None


# fmt: on
def test_revise_error():
    from julia.ipy import revise

    counter = [0]

    def throw():
        counter[0] += 1
        raise RuntimeError("fake revise error")

    revise_wrapper = revise.make_revise_wrapper(throw)

    revise.revise_errors = 0
    try:
        assert revise.revise_errors_limit == 1

        with pytest.warns(UserWarning) as record1:
            revise_wrapper()  # called
        assert len(record1) == 2
        assert "fake revise error" in record1[0].message.args[0]
        assert "Turning off Revise.jl" in record1[1].message.args[0]

        revise_wrapper()  # not called

        assert counter[0] == 1
        assert revise.revise_errors == 1
    finally:
        revise.revise_errors = 0


@pytest.mark.skipif(sys.version_info[0] < 3, reason="Python 2 not supported")
def test_completions():
    from IPython.core.completer import provisionalcompleter
    from julia.ipy.monkeypatch_completer import JuliaCompleter

    jc = JuliaCompleter()
    t = "%julia Base.si"
    with provisionalcompleter():
        completions = jc.julia_completions(t, len(t))
    assert {"sin", "sign", "sizehint!"} <= {c.text for c in completions}
