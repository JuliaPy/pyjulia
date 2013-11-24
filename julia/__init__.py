import sys
import imp
import keyword

from .core import Julia, JuliaModule, JuliaError

# initialize julia interpreter
julia = Julia()

# monkeypatch julia interpreter into module load path
#sys.modules["julia"] = julia

# add custom import behavior for the julia "module"
class JuliaImporter(object):

    def find_module(self, fullname, path=None):
        print((fullname, path))
        if path is None:
            pass
        if fullname.startswith("julia"):
            return JuliaModuleLoader()
        else:
           return None


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


def isamodule(julia_name):
    return julia.eval("isa({}, Module)".format(julia_name))


class JuliaModuleLoader(object):

    def load_module(self, fullname):
        juliapath = fullname.lstrip("julia.")
        if isamodule(juliapath):
            mod = sys.modules.setdefault(fullname, JuliaModule(fullname))
            mod.__loader__ = self
            names = julia.eval("names({})".format(juliapath))
            for name in names:
                if ismacro(name) or isoperator(name) or isprotected(name) or notascii(name):
                    continue
                attrname = name
                if name.endswith("!"):
                    attrname = name.rstrip("!") + "_b"
                if keyword.iskeyword(name):
                    attrname = "jl".join(name)
                try:
                    module_path = ".".join((juliapath, name))
                    module_obj = julia.eval(module_path)
                    is_module = julia.eval("isa({}, Module)".format(module_path))
                    if is_module:
                        split_path = module_path.split(".")
                        is_base = split_path[-1] == "Base"
                        recur_module = split_path[-1] == split_path[-2]
                        if is_module and not is_base and not recur_module:
                            newpath = ".".join((fullname, name))
                            module_obj = self.load_module(newpath)
                    is_function = julia.eval("isa({}, Function)".format(module_path))
                    if is_function:
                        pass
                    setattr(mod, attrname, module_obj)
                except Exception:
                    # some names cannot be imported from base
                    pass
            return mod

sys.meta_path.append(JuliaImporter())
