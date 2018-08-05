from IPython.testing.globalipapp import get_ipython
import julia.magic


def get_julia_magics():
    return julia.magic.JuliaMagics(shell=get_ipython())


def test_register_magics():
    julia.magic.load_ipython_extension(get_ipython())


def test_success_line():
    jm = get_julia_magics()
    ans = jm.julia('1')
    assert ans == 1


def test_success_cell():
    jm = get_julia_magics()
    ans = jm.julia(None, '2')
    assert ans == 2


def test_failure_line():
    jm = get_julia_magics()
    ans = jm.julia('pop!([])')
    assert ans is None


def test_failure_cell():
    jm = get_julia_magics()
    ans = jm.julia(None, '1 += 1')
    assert ans is None
