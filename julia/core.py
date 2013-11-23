"""
Bridge Python and Julia by initializing the Julia interpreter inside Python.
"""

#-----------------------------------------------------------------------------
# Copyright (C) 2013 The IPython and Julia Development Teams.
#
# Distributed under the terms of the BSD License. The full license is in
# the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Stdlib
import ctypes
import ctypes.util
import os
import sys
import keyword

from ctypes import c_void_p as void_p
from ctypes import c_char_p as char_p
from ctypes import py_object

# this is python 3.3 specific
from types import ModuleType, FunctionType
#-----------------------------------------------------------------------------
# Classes and funtions
#-----------------------------------------------------------------------------
python_version = sys.version_info

if python_version.major == 3 and python_version.minor >= 3:
    from collections import ChainMap

    class ModuleChainedDict(ChainMap, dict):
        pass
else:
    # http://code.activestate.com/recipes/305268/
    import UserDict

    class ModuleChainedDict(UserDict.DictMixin,dict):
        """Combine mulitiple mappings for seq lookup.
        For example, to emulate PYthon's normal lookup sequence:"
        import __builtin__
        pylookup = ChainMap(locals(), globals(), vars(__builtin__))
        """

        def __init__(self, *maps):
            self._maps = maps

        def __getitem__(self, key):
            for mapping in self._maps:
                try:
                    return mapping[key]
                except KeyError:
                    pass
            raise KeyError(key)


class MetaJuliaModule(type):
    def __new__(meta, name, bases, dict):
        mod = ModuleType(name, dict.get("__doc__"))
        for key, obj in dict.items():
            if isinstance(obj, FunctionType):
                obj = meta.chained_function(meta, obj, mod)
            mod.__dict__[key] = obj
        return mod

    def chained_function(meta, func, mod):
        d = ModuleChainedDict(mod.__dict__, func.__globals__)
        newfunc = FunctionType(func.__code, d)
        newfunc.__doc__ = func.__doc__
        newfunc.__defaults__ = newfunc.__defaults__
        newfunc.__kwdefaults__ = func.__kwdefaults__
        return newfunc


class JuliaObject(object):
    pass


class JuliaError(JuliaObject, Exception):
    pass


class JuliaModule(JuliaObject):
    pass


class JuliaFunction(JuliaObject):
    pass


def ismacro(name):
    return name.startswith("@")


def isoperator(name):
    return not name[0].isalpha()


class Julia(ModuleType):
    """Implements a bridge to the Julia interpreter or library.
    This uses the Julia PyCall module to perform type conversions and allow
    full access to the entire Julia interpreter.
    """

    def __init__(self, init_julia=True):
        """Create a Python object that represents a live Julia interpreter.

        Parameters
        ==========

        init_julia : bool
        If True, try to initialize the Julia interpreter. If this code is
        being called from inside an already running Julia, the flag should be
        passed as False so the interpreter isn't re-initialized.

        Note that it is safe to call this class constructor twice in the same
        process with `init_julia` set to True, as a global reference is kept
        to avoid re-initializing it. The purpose of the flag is only to manage
        situations when Julia was initialized from outside this code.
        """

        # Ugly hack to register the julia interpreter globally so we can reload
        # this extension without trying to re-open the shared lib, which kills
        # the python interpreter. Nasty but useful while debugging
        if hasattr(sys, '_julia_runtime'):
            self.api = sys._julia_runtime
            return

        if init_julia:
            if sys.platform.startswith("linux"):
                jpath = '/usr/lib/julia/libjulia.so'
            elif sys.platform.startswith("darwin"):
                jpath = '/usr/lib/julia/libjulia.dylib'
            elif sys.platform.startswith("win"):
                raise NotImplementedError("Windows is not supported yet")
            else:
                raise NotImplementedError("Unsupported operating system")

            if not os.path.exists(jpath):
                raise ValueError("Julia library not found!")

            api = ctypes.PyDLL(jpath, ctypes.RTLD_GLOBAL)
            api.jl_init.arg_types = [char_p]
            api.jl_init(0)
        else:
            # we're assuming here we're fully inside a running Julia process,
            # so we're fishing for symbols in our own process table
            api = ctypes.PyDLL('')

        # Store the running interpreter reference so we can start using it via
        # self.call
        self.api = api

        # Set the return types of some of the bridge functions in ctypes
        # terminology
        api.jl_eval_string.argtypes = [char_p]
        api.jl_eval_string.restype = void_p

        api.jl_exception_occurred.restype = void_p
        api.jl_call1.restype = void_p
        api.jl_get_field.restype = void_p
        api.jl_typename_str.restype = char_p
        api.jl_typeof_str.restype = char_p
        api.jl_unbox_voidpointer.restype = py_object

        #api.jl_bytestring_ptr.argtypes = [ctypes.c_void_p]
        #api.jl_bytestring_ptr.restype = ctypes.c_char_p

        if init_julia:
            # python_exe = os.path.basename(sys.executable)
            try:
                self.call('using PyCall')
            except:
                raise JuliaError("Julia does not have package PyCall")
            try:
                self.call('pyinitialize(C_NULL)')
            except:
                raise JuliaError("Failed to initialize PyCall package")

        # Whether we initialized Julia or not, we MUST create at least one
        # instance of PyObject. Since this will be needed on every call, we
        # hold it in the Julia object itself so it can survive across
        # reinitializations.
        api.PyObject = self.call('PyObject')

        # Flag process-wide that Julia is initialized and store the actual
        # runtime interpreter, so we can reuse it across calls and module
        # reloads.
        sys._julia_runtime = api
        basenames = []
        for name in self.names(self.Base):
            if ismacro(name):
                continue
            if isoperator(name):
                continue
            if name.endswith("!"):
                name = name.rstrip("!") + "_b"
            if keyword.iskeyword(name):
                name = "jl".join(name)
            basenames.append(name)
        self.basenames = basenames

    def __dir__(self):
        standard = super(Julia).__dir__()
        dirs = standard + self.basenames
        return dirs

    def call(self, src):
        """Low-level call to execute a snippet of Julia source.

        This only raises an exception if Julia itself throws an error, but it
        does NO type conversion into usable Python objects nor any memory
        management. It should never be used for returning the result of Julia
        expressions, only to execute statements.
        """
        byte_src = bytes(str(src).encode('ascii'))
        # ruturn null ptr if error
        ans = self.api.jl_eval_string(byte_src)
        if not ans:
            #TODO: introspect the julia error object
            #jexp = self.api.jl_exception_occurred()
            #msgptr = self.api.jl_get_field(jexp, b'msg')
            #msg = char_p(msgptr).value
            raise JuliaError('Exception calling julia src: \n{}'.format(src))
        return ans

    def help(self, name):
        """
        return help string..
        """
        if name is None:
            return None
        self.eval('help("{}")'.format(name))

    def methods(self, name):
        """
        return methods
        """
        if name is None:
            return None
        print(self.eval("string(methods({}))".format(name)))

    def put(self, x):
        pass

    def get(self, x):
        pass

    def __getattr__(self, attr):
        if attr is None:
            return None
        if attr in ['__name__', '__file__']:
            return super(Julia, self).__getattr__(attr)
        if attr.startswith("jl"):
            # attribute is a python builtin, rename
            julia_name = attr[2:]
        elif attr.endswith("_b"):
            # pycall always makes a copy across the interface so
            # inplace methods are not much use on the python side
            julia_name = attr.rstrip("_b") + "!"
        else:
            julia_name = attr
        try:
            obj = self.eval(julia_name)
            setattr(self, attr, obj)
            return obj
        except:
            raise AttributeError(attr)

    def eval(self, src):
        """
        Execute code in Julia, and pull some of the results back into the
        Python namespace.
        """
        if src is None:
            return None
        ans = self.call(src)
        res = self.api.jl_call1(void_p(self.api.PyObject), void_p(ans))
        if not res:
            #TODO: introspect the julia error object here
            raise JuliaError('ErrorException in Julia PyObject: '
                             '{}'.format(src))
        boxed_obj = self.api.jl_get_field(void_p(res), b'o')
        pyobj = self.api.jl_unbox_voidpointer(void_p(boxed_obj))
        # make sure we incref it before returning it,
        # since this is a borrowed reference
        ctypes.pythonapi.Py_IncRef(ctypes.py_object(pyobj))
        return pyobj
