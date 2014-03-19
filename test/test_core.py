import math
import unittest

from julia import Julia, JuliaError

class JuliaTest(unittest.TestCase):
    def setUp(self):
        self.julia = Julia()

    def tearDown(self):
        self.julia = None

    def test_call(self):
        self.julia.call('1 + 1')
        self.julia.call('sqrt(2.0)')

    def test_eval(self):
        self.assertEqual(2, self.julia.eval('1 + 1'))
        self.assertEqual(math.sqrt(2.0), self.julia.eval('sqrt(2.0)'))
        self.assertEqual(1, self.julia.eval('PyObject(1)'))
        self.assertEqual(1000, self.julia.eval('PyObject(1000)'))
        self.assertEqual((1, 2, 3), self.julia.eval('PyObject((1, 2, 3))'))

    def test_call_error(self):
        try:
            self.julia.call('undefined_function_name()')
            self.fail('No error?')
        except JuliaError:
            pass

