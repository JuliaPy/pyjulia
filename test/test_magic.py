from IPython.testing.globalipapp import get_ipython
import julia.magic


def test_register_magics():
    julia.magic.load_ipython_extension(get_ipython())
