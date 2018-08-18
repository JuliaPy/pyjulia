from __future__ import print_function

import array
import math
import subprocess
import unittest
from contextlib import contextmanager
from types import ModuleType

from julia import Julia, JuliaError
from julia.core import jl_name, py_name
import sys
import os

import pytest

python_version = sys.version_info


orig_env = os.environ.copy()
julia = Julia(runtime=os.getenv("JULIA_EXE"), debug=True)


class JuliaTest(unittest.TestCase):

    def test_call(self):
        julia._call('1 + 1')
        julia._call('sqrt(2.0)')

    def test_eval(self):
        self.assertEqual(2, julia.eval('1 + 1'))
        self.assertEqual(math.sqrt(2.0), julia.eval('sqrt(2.0)'))
        self.assertEqual(1, julia.eval('PyObject(1)'))
        self.assertEqual(1000, julia.eval('PyObject(1000)'))
        self.assertEqual((1, 2, 3), julia.eval('PyObject((1, 2, 3))'))

    def test_call_error(self):
        msg = "Error with message"
        try:
            julia._call('error("{}")'.format(msg))
            self.fail('No error?')
        except JuliaError as err:
            self.assertIn(msg, err.args[0])

    def test_call_julia_function_with_python_args(self):
        self.assertEqual(['A', 'B', 'C'],
                         list(julia.map(julia.uppercase,
                                        array.array('u', [u'a', u'b', u'c']))))
        self.assertEqual([1.0, 2.0, 3.0],
                         list(julia.map(julia.floor, [1.1, 2.2, 3.3])))
        self.assertEqual(1.0, julia.cos(0))

    def test_call_julia_with_python_callable(self):
        def add(a, b):
            return a + b
        self.assertSequenceEqual([1, 4, 9],
                                 list(julia.map(lambda x: x * x, [1, 2, 3])))
        self.assertTrue(all(x == y for x, y in zip([11, 11, 11],
                         julia.map(lambda x: x + 1,
                                   array.array('I', [10, 10, 10])))))
        self.assertEqual(6, julia.reduce(add, [1, 2, 3]))

    def test_call_python_with_julia_args(self):
        self.assertEqual(6, sum(julia.eval('(1, 2, 3)')))
        self.assertEqual([1, 4, 9], list(map(julia.eval("x->x^2"), [1, 2, 3])))

    def test_import_julia_functions(self):
        if (python_version.major < 3 or
            (python_version.major == 3 and python_version.minor < 3)):
            import julia.sum as julia_sum
            self.assertEqual(6, julia_sum([1, 2, 3]))
        else:
            pass

    def test_import_julia_module_existing_function(self):
        from julia import Base
        assert Base.mod(2, 2) == 0

    def test_from_import_existing_julia_function(self):
        from julia.Base import divrem
        assert divrem(7, 3) == (2, 1)

    def test_import_julia_module_non_existing_name(self):
        from julia import Base
        try:
            Base.spamspamspam
            self.fail('No AttributeError')
        except AttributeError:
            pass

    def test_from_import_non_existing_julia_name(self):
        try:
            from Base import spamspamspam
        except ImportError:
            pass
        else:
            assert not spamspamspam

    def test_julia_module_bang(self):
        from julia.Base import Channel, put_b, take_b
        chan = Channel(1)
        sent = 123
        put_b(chan, sent)
        received = take_b(chan)
        assert sent == received

    def test_import_julia_submodule(self):
        from julia.Base import Enums
        assert isinstance(Enums, ModuleType)

    def test_star_import_julia_module(self):
        from . import _star_import
        _star_import.Enum

    def test_main_module(self):
        from julia import Main
        Main.x = x = 123456
        assert julia.eval('x') == x

    def test_module_all(self):
        from julia import Base
        assert 'resize_b' in Base.__all__

    def test_module_dir(self):
        from julia import Base
        assert 'resize_b' in dir(Base)

    @pytest.mark.skipif(
        "JULIA_EXE" in orig_env,
        reason=("cannot be tested with custom Julia executable;"
                " JULIA_EXE is set to {}".format(orig_env.get("JULIA_EXE"))))
    def test_import_without_setup(self):
        command = [sys.executable, '-c', 'from julia import Base']
        print('Executing:', *command)
        subprocess.check_call(command, env=orig_env)

    #TODO: this causes a segfault
    """
    def test_import_julia_modules(self):
        import julia.PyCall as pycall
        self.assertEquals(6, pycall.pyeval('2 * 3'))
    """

    def test_jlpy_identity(self):
        for name in ['normal', 'resize!']:
            self.assertEqual(jl_name(py_name(name)), name)

    def test_pyjl_identity(self):
        for name in ['normal', 'resize_b']:
            self.assertEqual(py_name(jl_name(name)), name)
