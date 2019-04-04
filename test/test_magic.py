from IPython.testing.globalipapp import start_ipython as _start_ipython
from IPython import get_ipython as _get_ipython
from julia import magic
import pytest

def get_ipython():
    return _start_ipython() or _get_ipython()

@pytest.fixture
def julia_magics(julia):
    return magic.JuliaMagics(shell=get_ipython())


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


def test_interp_var(julia_magics):
    assert julia_magics.shell.run_cell("""
    x=1
    %julia $x
    """).result == 1
    
def test_interp_expr(julia_magics):
    assert julia_magics.shell.run_cell("""
    x=1
    %julia py"x+1"
    """).result == 2
    
def test_bad_interp(julia_magics):
    assert julia_magics.shell.run_cell("""
    %julia $(x+1)
    """).error_in_exec is not None
    
def test_string_interp(julia_magics):
    assert julia_magics.shell.run_cell("""
    %julia foo=3; "$foo"    
    """).result == '3'
    
def test_interp_escape(julia_magics):
    assert julia_magics.shell.run_cell("""
    %julia bar=3; :($$bar)
    """).result == 3
    
def test_type_conversion(julia_magics):
    assert julia_magics.shell.run_cell("""
    %julia py"1" isa Int && py"1"o isa PyObject
    """).result == True
    
def test_scoping(julia_magics):
    assert julia_magics.shell.run_cell("""
    x = "global"
    def f():
        x = "local"
        ret = %julia py"x"
        return ret
    f()    
    """).result == "local"
    
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
