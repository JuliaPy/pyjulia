from __future__ import absolute_import, print_function

import textwrap


class OptionDescriptor(object):
    @property
    def dataname(self):
        return "_" + self.name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return getattr(instance, self.dataname, self.default)

    def cli_argument_name(self):
        name = {"bindir": "home"}.get(self.name, self.name)
        return "--" + name.replace("_", "-")

    def cli_argument_spec(self):
        return dict(help="Julia's ``{}`` option.".format(self.cli_argument_name()))
        # TODO: parse help from `options_docs`.


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

    def _domain(self):  # used in test
        return str


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

    def _domain(self):  # used in test
        return set(self.choicemap)

    def cli_argument_spec(self):
        return dict(
            super(Choices, self).cli_argument_spec(),
            choices=list(self.choicemap.values()),
        )


def yes_no_etc(*etc):
    choicemap = {True: "yes", False: "no", "yes": "yes", "no": "no"}
    for v in etc:
        choicemap[v] = v
    return choicemap


options_docs = """
bindir: str
    Set location of `julia` executable relative to which we find
    system image (``sys.so``).  It is inferred from `runtime` if not
    given.  Equivalent to ``--home`` of the Julia CLI.

check_bounds: {True, False, 'yes', 'no'}
    Emit bounds checks always or never (ignoring declarations).
    `True` and `False` are synonym of ``'yes'`` and ``'no'``, respectively.
    This applies to all other options.

compile: {True, False, 'yes', 'no', 'all', 'min'}
    Enable or disable JIT compiler, or request exhaustive compilation.

compiled_modules: {True, False, 'yes', 'no'}
    Enable or disable incremental precompilation of modules.

depwarn: {True, False, 'yes', 'no', 'error'}
    Enable or disable syntax and method deprecation warnings ("error"
    turns warnings into errors).

inline: {True, False, 'yes', 'no'}
    Control whether inlining is permitted, including overriding
    @inline declarations.

optimize: {0, 1, 2, 3}
    Set the optimization level (default level is 2 if unspecified or 3
    if used without a level).

sysimage: str
    Start up with the given system image file.

warn_overwrite: {True, False, 'yes', 'no'}
    Enable or disable method overwrite warnings.
"""


class JuliaOptions(object):
    """
    Julia options validator.

    Attributes
    ----------
    """

    __doc__ = textwrap.dedent(__doc__) + options_docs

    # `options_docs` defined above must be updated when changing the
    # list of options supported by `JuliaOptions`. `test_options_docs`
    # tests that `options_docs` matches with the definition of
    # `JuliaOptions`

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
                yield getattr(self.__class__, name), getattr(self, name)

    def as_args(self):
        args = []
        for (desc, value) in self.specified():
            args.append(desc.cli_argument_name())
            args.append(value)
        return args

    @classmethod
    def supported_options(cls):
        for name in dir(cls):
            if cls.is_supported(name):
                yield getattr(cls, name)


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
