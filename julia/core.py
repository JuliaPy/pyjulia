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
import warnings

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

    class ModuleChainedDict(UserDict.DictMixin, dict):
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


if python_version.major == 3:
    from io import StringIO
else:
    from cStringIO import StringIO


class JuliaOutput(list):

    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        sys.stdout = self._stdout


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


# add custom import behavior for the julia "module"
class JuliaImporter(object):
    def __init__(self, julia):
        self.julia = julia

    def find_module(self, fullname, path=None):
        if path is None:
            pass
        if fullname.startswith("julia."):
            return JuliaModuleLoader(self.julia)


class JuliaModuleLoader(object):

    def __init__(self, julia):
        self.julia = julia

    def load_module(self, fullname):
        juliapath = fullname.lstrip("julia.")
        if isamodule(self.julia, juliapath):
            mod = sys.modules.setdefault(fullname, JuliaModule(fullname))
            mod.__loader__ = self
            names = self.julia.eval("names({}, true, false)".format(juliapath))
            for name in names:
                if (ismacro(name) or
                    isoperator(name) or
                    isprotected(name) or
                    notascii(name)):
                    continue
                attrname = name
                if name.endswith("!"):
                    attrname = name.replace("!", "_b")
                if keyword.iskeyword(name):
                    attrname = "jl".join(name)
                try:
                    module_path = ".".join((juliapath, name))
                    module_obj = self.julia.eval(module_path)
                    is_module = self.julia.eval("isa({}, Module)"
                                                .format(module_path))
                    if is_module:
                        split_path = module_path.split(".")
                        is_base = split_path[-1] == "Base"
                        recur_module = split_path[-1] == split_path[-2]
                        if is_module and not is_base and not recur_module:
                            newpath = ".".join((fullname, name))
                            module_obj = self.load_module(newpath)
                    setattr(mod, attrname, module_obj)
                except Exception:
                    if isafunction(self.julia, name, mod_name=juliapath):
                        func = "{}.{}".format(juliapath, name)
                        setattr(mod, name, self.julia.eval(func))
                    # TODO:
                    # some names cannot be imported from base
                    #warnings.warn("cannot import {}".format(name))
                    pass
            return mod
        elif isafunction(self.julia, juliapath):
            return getattr(self.julia, juliapath)


class JuliaObject(object):
    pass


class JuliaError(JuliaObject, Exception):
    pass


class JuliaModule(ModuleType):
    pass


class JuliaFunction(JuliaObject):
    pass


def ismacro(name):
    return name.startswith("@")


def isoperator(name):
    return not name[0].isalpha()


def isprotected(name):
    return name.startswith("_")


def notascii(name):
    try:
        name.encode("ascii")
        return False
    except:
        return True


def isamodule(julia, julia_name):
    try:
        ret = julia.eval("isa({}, Module)".format(julia_name))
        return ret
    except:
        # try explicitly importing it..
        try:
            julia.eval("import {}".format(julia_name))
            ret = julia.eval("isa({}, Module)".format(julia_name))
            return ret
        except:
            pass
    return False


def isafunction(julia, julia_name, mod_name=""):
    code = "isa({}, Function)".format(julia_name)
    if mod_name:
        code = "isa({}.{}, Function)".format(mod_name, julia_name)
    try:
        return julia.eval(code)
    except:
        return False


def base_functions(julia):
    bases = {}
    names = julia.eval("names(Base)")
    for name in names:
        if (ismacro(name) or
            isoperator(name) or
            isprotected(name) or
            notascii(name)):
            continue
        try:
            # skip modules for now
            if isamodule(julia, name):
                continue
            if name.startswith("_"):
                continue
            if not isafunction(julia, name):
                continue
            attr_name = name
            if name.endswith("!"):
                attr_name = name.replace("!", "_b")
            if keyword.iskeyword(name):
                attr_name = "jl".join(name)
            julia_func = julia.eval(name)
            bases[attr_name] = julia_func
        except:
            pass
    return bases


class Julia(object):
    """Implements a bridge to the Julia interpreter or library.
    This uses the Julia PyCall module to perform type conversions and allow
    full access to the entire Julia interpreter.
    """

    def __init__(self, init_julia=True, jl_init_path=None):
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
            jpath = ''
            if sys.platform.startswith("linux"):
                jpath = '/usr/lib/julia/libjulia.so'
                if not os.path.exists(jpath):
                    #XXX: TEMPORARY HACK TO WORK ON TRAVIS
                    jpath = '/usr/lib/x86_64-linux-gnu/julia/libjulia.so'
            elif sys.platform.startswith("darwin"):
                jpath = '/usr/lib/julia/libjulia.dylib'
            elif sys.platform.startswith("win"):
                lib_file_name = 'libjulia.dll'
                # try to locate path of julia from environ
                possible_env_key = ('JULIA_HOME', 'JULIAHOME',
                                    'JULIA_PATH', 'JULIAPATH',
                                    'JULIA_ROOT', 'JULIAROOT')
                for env_key in possible_env_key:
                    env = os.getenv(env_key)
                    if env:
                        # Though the argument of jl_init is named
                        # julia_home_dir, the actually path in use is
                        # `julia_home_dir/../lib/julia/sys.ji', rather than
                        # `julia_home_dir/lib/julia/sys.ji'.
                        # If users set JULIA_HOME to, say, `D:\julia0.2.0',
                        # which is totally reasonable, the julia interpreter
                        # won't start due to wrong path of `sys.ji'.
                        # So on Windows, if users want their julia interpreter
                        # being available, they probably have to set
                        # JULIA_HOME to `D:\julia0.2.0\bin' so that `sys.ji'
                        # will be loaded.
                        jpath = os.path.join(env, lib_file_name)
                        break
                else:
                    # not found in the possible environ keys,
                    # search for julia in %PATH%
                    for path in os.getenv('PATH').split(';'):
                        if 'julia' in path:
                            jpath = os.path.join(path, lib_file_name)
                            break
                # The argument of jl_init seems unreasonable.
                # If None is given to jl_init, the path of current Python
                # interpreter will be used, which results in a path like
                # `C:\Python27\../lib/julia/sys.ji'.
                # So at least on windows, the argument of jl_init must be
                # specified.
                jl_init_path = os.path.dirname(jpath)
            else:
                raise NotImplementedError("Unsupported operating system")

            if not os.path.exists(jpath):
                raise ValueError("Julia library not found!")

            api = ctypes.PyDLL(jpath, ctypes.RTLD_GLOBAL)
            api.jl_init.arg_types = [char_p]

            if jl_init_path:
                if python_version.major == 3:  # we need to translate in non-unicode
                    sys_ji_path_relative = os.path.join("..", "lib", "julia", "sys.ji")
                    api.jl_init_with_image(jl_init_path.encode(), sys_ji_path_relative.encode())
                else:    
                    api.jl_init(jl_init_path)
            else:
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
        api.jl_typeof_str.argtypes = [void_p]
        api.jl_typeof_str.restype = char_p
        api.jl_call1.restype = void_p
        api.jl_get_field.restype = void_p
        api.jl_typename_str.restype = char_p
        api.jl_typeof_str.restype = char_p
        api.jl_unbox_voidpointer.restype = py_object

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

        self.bases = base_functions(self)
        sys.meta_path.append(JuliaImporter(self))

    def call(self, src):
        """Low-level call to execute a snippet of Julia source.

        This only raises an exception if Julia itself throws an error, but it
        does NO type conversion into usable Python objects nor any memory
        management. It should never be used for returning the result of Julia
        expressions, only to execute statements.
        """
        byte_src = bytes(str(src).encode('ascii'))
        # return null ptr if error
        ans = self.api.jl_eval_string(byte_src)
        if not ans:
            jexp = self.api.jl_exception_occurred()
            exception_str = self._unwrap_exception(jexp)
            raise JuliaError('Exception calling julia src: {}\n{}'
                             .format(exception_str, src))
        return ans

    def _unwrap_exception(self, jl_exc):
        exception = void_p.in_dll(self.api, 'jl_exception_in_transit')
        msg = self.api.jl_typeof_str(exception)
        return char_p(msg).value

    def help(self, name):
        """
        return help string..
        """
        if name is None:
            return None
        self.eval('help("{}")'.format(name))

    def __getattr__(self, name):
        bases = object.__getattribute__(self, 'bases')
        if not name in bases:
            raise AttributeError("Name {} not found".format(name))
        return bases[name]

    def put(self, x):
        pass

    def get(self, x):
        pass

    #TODO: use convert(PyAny, PyObj) for "putting python objects into julia"

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
            raise JuliaError("ErrorException in Julia PyObject: "
                             "{}".format(src))
        boxed_obj = self.api.jl_get_field(void_p(res), b'o')
        pyobj = self.api.jl_unbox_voidpointer(void_p(boxed_obj))
        # make sure we incref it before returning it,
        # since this is a borrowed reference
        ctypes.pythonapi.Py_IncRef(ctypes.py_object(pyobj))
        return pyobj
