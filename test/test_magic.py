from textwrap import dedent

import pytest
from IPython import get_ipython as _get_ipython
from IPython.testing.globalipapp import start_ipython as _start_ipython

from julia import magic


def get_ipython():
    return _start_ipython() or _get_ipython()

@pytest.fixture
def julia_magics(julia):
    julia_magics = magic.JuliaMagics(shell=get_ipython())
    
    # a more conenient way to run strings (possibly with magic) as if they were
    # an IPython cell
    def run_cell(self, cell):
        cell = dedent(cell).strip()
        if cell.startswith("%%"):
            return self.shell.run_cell_magic("julia","",cell.replace("%%julia","").strip())
        else:
            exec_result = self.shell.run_cell(cell)
            if exec_result.error_in_exec:
                raise exec_result.error_in_exec
            else:
                return exec_result.result
                
    julia_magics.run_cell = run_cell.__get__(julia_magics, julia_magics.__class__)
    
    return julia_magics



def test_register_magics(julia):
    magic.load_ipython_extension(get_ipython())


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


# Prior to IPython 7.3, $x did a string interpolation handled by IPython itself
# for *line* magic, and could not be turned off. However, even prior to
# IPython 7.3, *cell* magic never did the string interpolation, so below, any
# time we need to test $x interpolation, do it as cell magic so it works on
# IPython < 7.3

def test_interp_var(julia_magics):
    julia_magics.run_cell("x=1")
    assert julia_magics.run_cell("""
    %%julia
    $x
    """) == 1
    
def test_interp_expr(julia_magics):
    assert julia_magics.run_cell("""
    x=1
    %julia py"x+1"
    """) == 2

def test_bad_interp(julia_magics):
    with pytest.raises(Exception):
        assert julia_magics.run_cell("""
        %julia $(x+1)
        """)

def test_string_interp(julia_magics):
    assert julia_magics.run_cell("""
    %%julia 
    foo=3
    "$foo"
    """) == '3'

def test_interp_escape(julia_magics):
    assert julia_magics.run_cell("""
    %%julia
    bar=3
    :($$bar)
    """) == 3

def test_type_conversion(julia_magics):
    assert julia_magics.run_cell("""
    %julia py"1" isa Integer && py"1"o isa PyObject
    """) == True

def test_scoping(julia_magics):
    assert julia_magics.run_cell("""
    x = "global"
    def f():
        x = "local"
        ret = %julia py"x"
        return ret
    f()    
    """) == "local"

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
