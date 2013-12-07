import sys
import keyword

from .core import Julia, JuliaModule


# initialize julia interpreter
julia = Julia()


# add custom import behavior for the julia "module"
class JuliaImporter(object):

    def find_module(self, fullname, path=None):
        if path is None:
            pass
        if fullname.startswith("julia."):
            return JuliaModuleLoader()


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


def isafunction(julia_name):
    return julia.eval("isa({}, Function)".format(julia_name))


class JuliaModuleLoader(object):

    def load_module(self, fullname):
        juliapath = fullname.lstrip("julia.")
        if isamodule(juliapath):
            mod = sys.modules.setdefault(fullname, JuliaModule(fullname))
            mod.__loader__ = self
            names = julia.eval("names({}, true, false)"
                               .format(juliapath))
            for name in names:
                if (ismacro(name) or
                    isoperator(name) or
                    isprotected(name) or
                    notascii(name)):
                    continue
                attrname = name
                if name.endswith("!"):
                    attrname = name.replace("!", "_bang")
                if keyword.iskeyword(name):
                    attrname = "jl".join(name)
                try:
                    module_path = ".".join((juliapath, name))
                    module_obj = julia.eval(module_path)
                    is_module = julia.eval("isa({}, Module)"
                                           .format(module_path))
                    if is_module:
                        split_path = module_path.split(".")
                        is_base = split_path[-1] == "Base"
                        recur_module = split_path[-1] == split_path[-2]
                        if (is_module and not
                            is_base and not
                            recur_module):
                            newpath = ".".join((fullname, name))
                            module_obj = self.load_module(newpath)
                    setattr(mod, attrname, module_obj)
                except Exception:
                    # TODO:
                    # some names cannot be imported from base
                    pass
            return mod


# monkeypatch julia interpreter into module load path
sys.meta_path.append(JuliaImporter())


def base_functions():
    thismodule = sys.modules[__name__]
    names = julia.eval("names(Base)")
    for name in names:
        if (ismacro(name) or
            isoperator(name) or
            isprotected(name) or
            notascii(name)):
            continue
        try:
            # skip modules for now
            if isamodule(name):
                continue
            if name.startswith("_"):
                continue
            if not isafunction(name):
                continue
            attr_name = name
            if name.endswith("!"):
                attr_name = name.replace("!", "_b")
            if keyword.iskeyword(name):
                attr_name = "jl".join(name)
            julia_func = julia.eval(name)
            setattr(thismodule, attr_name, julia_func)
        except:
            pass


base_functions()


def eval(src):
    return julia.eval(src)
