from __future__ import print_function, absolute_import


class OptionDescriptor(object):
    @property
    def dataname(self):
        return "_" + self.name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return getattr(instance, self.dataname, self.default)


class String(OptionDescriptor):
    def __init__(self, name, default=None):
        self.name = name
        self.default = default

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError(self.name)
        if value == self.default or isinstance(value, str):
            setattr(instance, self.dataname, value)
        else:
            raise ValueError(
                "Option {!r} only accepts `str`. Got: {!r}".format(self.name, value)
            )

    def show_option(self):
        print(self.name, "(string)", end="")


class Choices(OptionDescriptor):
    def __init__(self, name, choicemap, default=None):
        self.name = name
        self.choicemap = choicemap
        self.default = default

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError(self.name)
        if value == self.default:
            setattr(instance, self.dataname, value)
        elif value in self.choicemap:
            setattr(instance, self.dataname, self.choicemap[value])
        else:
            raise ValueError(
                "Option {!r} does not accept {!r}".format(self.name, value)
            )

    def show_option(self):
        print(self.name, ":", end="")
        for var in self.choicemap:
            print("", repr(var), end="")


def yes_no_etc(*etc):
    choicemap = {True: "yes", False: "no", "yes": "yes", "no": "no"}
    for v in etc:
        choicemap[v] = v
    return choicemap


class JuliaOptions(object):

    sysimage = String("sysimage")
    bindir = String("bindir")
    compiled_modules = Choices("compiled_modules", yes_no_etc())
    compile = Choices("compile", yes_no_etc("all", "min"))
    depwarn = Choices("depwarn", yes_no_etc("error"))
    warn_overwrite = Choices("warn_overwrite", yes_no_etc())
    optimize = Choices("optimize", dict(zip(range(4), range(4))))
    inline = Choices("inline", yes_no_etc())
    check_bounds = Choices("check_bounds", yes_no_etc())

    def __init__(self, **kwargs):
        unsupported = []
        for (name, value) in kwargs.items():
            if self.is_supported(name):
                setattr(self, name, value)
            else:
                unsupported.append(name)
        if unsupported:
            raise TypeError(
                "Unsupported Julia option(s): {}".format(", ".join(unsupported))
            )

    @classmethod
    def is_supported(cls, name):
        return isinstance(getattr(cls, name, None), OptionDescriptor)

    def is_specified(self, name):
        desc = getattr(self.__class__, name)
        if isinstance(desc, OptionDescriptor):
            return getattr(self, name) != desc.default
        return False

    def specified(self):
        for name in dir(self.__class__):
            if self.is_specified(name):
                yield name, getattr(self, name)

    def as_args(self):
        args = []
        for (name, value) in self.specified():
            name = {"bindir": "home"}.get(name, name)
            args.append("--" + name.replace("_", "-"))
            args.append(value)
        return args

    @classmethod
    def supported_names(cls):
        for name in dir(cls):
            if cls.is_supported(name):
                yield name

    @classmethod
    def show_supported(cls):
        print("** Supported options and possible values **")
        print("See `julia --help` for their effects.")
        print()
        for name in cls.supported_names():
            getattr(cls, name).show_option()
            print()


def parse_jl_options(options):
    """
    Parse --home and --sysimage options.

    Examples
    --------
    >>> ns = parse_jl_options(["--home", "PATH/TO/HOME"])
    >>> ns
    Namespace(home='PATH/TO/HOME', sysimage=None)
    >>> ns.home
    'PATH/TO/HOME'
    >>> parse_jl_options([])
    Namespace(home=None, sysimage=None)
    >>> parse_jl_options(["-HHOME", "--sysimage=PATH/TO/sys.so"])
    Namespace(home='HOME', sysimage='PATH/TO/sys.so')
    """
    import argparse

    def exit(*_):
        raise Exception("`exit` must not be called")

    def error(message):
        raise RuntimeError(message)

    parser = argparse.ArgumentParser()
    parser.add_argument("--home", "-H")
    parser.add_argument("--sysimage", "-J")

    parser.exit = exit
    parser.error = error
    ns, _ = parser.parse_known_args(options)
    return ns
