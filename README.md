PyJulia
=======

[![Build Status](https://travis-ci.org/JuliaPy/pyjulia.svg?branch=master)](https://travis-ci.org/JuliaPy/pyjulia)
[![Build status](https://ci.appveyor.com/api/projects/status/github/JuliaPy/pyjulia?svg=true)](https://ci.appveyor.com/project/Keno/pyjulia)

Experimenting with developing a better interface to [Julia language](https://julialang.org/) that works with [Python](https://www.python.org/) 2 & 3 and Julia v0.6+.

PyJulia is tested against Python versions 2.7, 3.5, 3.6, and 3.7.

Installation
------------

**Note:** If you are using Python installed with Ubuntu or `conda`,
PyJulia may not work with Julia ≥ 0.7.  For workarounds, see
[Troubleshooting](#troubleshooting) below.  Same caution applies to
any Debian-based and possibly other GNU/Linux distributions.

You will need to install PyCall in your existing Julia installation

```julia
julia> using Pkg  # for julia ≥ 0.7
julia> Pkg.add("PyCall")
```

Your python installation must be able to call command line program
`julia`.  If your installer does not add the Julia binary directory to
your `PATH`, you will have to add it.  _An alias will not work._

Then finally you have to install PyJulia.

**Note:** If you are not familiar with `pip` and have some troubles
with the following installation steps, we recommend going through the
[Tutorials in Python Packaging User Guide](https://packaging.python.org/tutorials/).

To get released versions you can use:

```console
$ python3 -m pip install --user julia
$ python2 -m pip install --user julia  # If you need Python 2
```

where `--user` should be omitted if you are using virtual environment
(`virtualenv`, `venv`, `conda`, etc.).

If you are interested in using the development version, you can
install PyJulia directly from GitHub:

```console
$ python3 -m pip install --user 'https://github.com/JuliaPy/pyjulia/archive/master.zip#egg=julia'
```

You may clone it directly to (say) your home directory.

```console
$ git clone https://github.com/JuliaPy/pyjulia
```

then inside the `pyjulia` directory you need to run the python setup file

```console
$ cd pyjulia
$ python3 -m pip install --user .
$ python3 -m pip install --user -e .  # If you want "development install"
```

The `-e` flag makes a development install, meaning that any change to PyJulia
source tree will take effect at next python interpreter restart without having
to reissue an install command.

See [Testing](#testing) below for how to run tests.

Usage
-----

PyJulia provides a high-level interface which assumes a "normal" setup
(e.g., `julia` program is in your `PATH`) and a low-level interface
which can be used in a customized setup.

### High-level interface

To call a Julia function in a Julia module, import the Julia module
(say `Base`) with:

```pycon
>>> from julia import Base
```

and then call Julia functions in `Base` from python, e.g.,

```pycon
>>> Base.sind(90)
```

Other variants of Python import syntax also work:

```pycon
>>> import julia.Base
>>> from julia.Base import Enums    # import a submodule
>>> from julia.Base import sin      # import a function from a module
```

The global namespace of Julia's interpreter can be accessed via a
special module `julia.Main`:

```pycon
>>> from julia import Main
```

You can set names in this module to send Python values to Julia:

```pycon
>>> Main.xs = [1, 2, 3]
```

which allows it to be accessed directly from Julia code, e.g., it can
be evaluated at Julia side using Julia syntax:

```pycon
>>> Main.eval("sin.(xs)")
```

### Low-level interface

If you need a custom setup for PyJulia, it must be done *before*
importing any Julia modules.  For example, to use the Julia
executable named `custom_julia`, run:

```pycon
>>> from julia import Julia
>>> jl = julia.Julia(runtime="custom_julia")
```

You can then use, e.g.,

```pycon
>>> from julia import Base
```

### IPython magic

In IPython (and therefore in Jupyter), you can directly execute Julia
code using `%%julia` magic:

```
In [1]: %load_ext julia.magic
Initializing Julia interpreter. This may take some time...

In [2]: %%julia
   ...: Base.banner(IOContext(stdout, :color=>true))
               _
   _       _ _(_)_     |  Documentation: https://docs.julialang.org
  (_)     | (_) (_)    |
   _ _   _| |_  __ _   |  Type "?" for help, "]?" for Pkg help.
  | | | | | | |/ _` |  |
  | | |_| | | | (_| |  |  Version 1.0.1 (2018-09-29)
 _/ |\__'_|_|_|\__'_|  |  Official https://julialang.org/ release
|__/                   |
```

### Virtual environments

PyJulia can be used in Python virtual environments created by
`virtualenv`, `venv`, and any tools wrapping them such as `pipenv`,
provided that Python executable used in such environments are linked
to identical libpython used by PyCall.  If this is not the case,
initializing PyJulia (e.g., `import julia.Main`) prints an informative
error message with detected paths to libpython.  See
[PyCall documentation](https://github.com/JuliaPy/PyCall.jl) for how
to configure Python executable.

Note that Python environment created by `conda` is not supported.

Troubleshooting
---------------

### Your Python interpreter is statically linked to libpython

If you use Python installed with Debian-based Linux distribution such
as Ubuntu or install Python by `conda`, you might have noticed that
PyJulia cannot be initialized properly with Julia ≥ 0.7.  This is
because those Python executables are statically linked to libpython.
(See [Limitations](#limitations) below for why that's a problem.)

If you are unsure if your `python` has this problem, you can quickly
check it by:

```console
$ ldd /usr/bin/python
        linux-vdso.so.1 (0x00007ffd73f7c000)
        libpthread.so.0 => /usr/lib/libpthread.so.0 (0x00007f10ef84e000)
        libc.so.6 => /usr/lib/libc.so.6 (0x00007f10ef68a000)
        libpython3.7m.so.1.0 => /usr/lib/libpython3.7m.so.1.0 (0x00007f10ef116000)
        /lib64/ld-linux-x86-64.so.2 => /usr/lib64/ld-linux-x86-64.so.2 (0x00007f10efaa4000)
        libdl.so.2 => /usr/lib/libdl.so.2 (0x00007f10ef111000)
        libutil.so.1 => /usr/lib/libutil.so.1 (0x00007f10ef10c000)
        libm.so.6 => /usr/lib/libm.so.6 (0x00007f10eef87000)
```

in Linux where `/usr/bin/python` should be replaced with the path to
your `python` command (use `which python` to find it out).  In macOS,
use `otool -L` instead of `ldd`.  If it does not print the path to
libpython like `/usr/lib/libpython3.7m.so.1.0` in above example, you
need to use one of the workaround below.

The easiest workaround is to use the `python-jl` command bundled in
PyJulia.  This can be used instead of normal `python` command for
basic use-cases such as:

```console
$ python-jl your_script.py
$ python-jl -c 'from julia.Base import banner; banner()'
$ python-jl -m IPython
```

See `python-jl --help` for more information.

Note that `python-jl` works by launching Python interpreter inside
Julia.  Importantly, it means that PyJulia has to be installed in the
Python environment with which PyCall is configured.  That is to say,
following commands must work for `python-jl` to be usable:

```julia
julia> using PyCall

julia> pyimport("julia")
PyObject <module 'julia' from '/.../julia/__init__.py'>
```

In fact, you can simply use PyJulia inside the Julia REPL, if you are
comfortable with working in it:

```julia
julia> using PyCall

julia> py"""
       from julia import Julia
       Julia(init_julia=False)

       from your_module_using_pyjulia import function
       function()
       """
```

Alternatively, you can use [pyenv](https://github.com/pyenv/pyenv) to
build Python with
[`--enable-shared` option](https://github.com/pyenv/pyenv/wiki#how-to-build-cpython-with---enable-shared).
Of course, manually building from Python source distribution with the
same configuration also works.

```console
$ PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.6.6
Downloading Python-3.6.6.tar.xz...
-> https://www.python.org/ftp/python/3.6.6/Python-3.6.6.tar.xz
Installing Python-3.6.6...
Installed Python-3.6.6 to /home/USER/.pyenv/versions/3.6.6

$ ldd ~/.pyenv/versions/3.6.6/bin/python3.6 | grep libpython
        libpython3.6m.so.1.0 => /home/USER/.pyenv/versions/3.6.6/lib/libpython3.6m.so.1.0 (0x00007fca44c8b000)
```

For more discussion, see:
https://github.com/JuliaPy/pyjulia/issues/185

### Segmentation fault in IPython

You may experience segmentation fault when using PyJulia in old
versions of IPython.  You can avoid this issue by updating IPython to
7.0 or above.  Alternatively, you can use IPython via Jupyter (e.g.,
`jupyter console`) to workaround the problem.


How it works
------------
PyJulia loads the `libjulia` library and executes the statements therein.
To convert the variables, the `PyCall` package is used. Python references
to Julia objects are reference counted by Python, and retained in the
`PyCall.pycall_gc` mapping on the Julia side (the mapping is removed
when reference count drops to zero, so that the Julia object may be freed).



Limitations
------------

### Mismatch in valid set of identifiers

Not all valid Julia identifiers are valid Python identifiers.  Unicode
identifiers are invalid in Python 2.7 and so PyJulia cannot call or
access Julia methods/variables with names that are not ASCII only.
Although Python 3 allows Unicode identifiers, they are more
aggressively normalized than Julia.  For example, `ϵ` (GREEK LUNATE
EPSILON SYMBOL) and `ε` (GREEK SMALL LETTER EPSILON) are identical in
Python 3 but different in Julia.  Additionally, it is a common idiom
in Julia to append a `!` character to methods which mutate their
arguments.  These method names are invalid Python identifers.
PyJulia renames these methods by subsituting `!` with `_b`.  For
example, the Julia method `sum!` can be called in PyJulia using
`sum_b(...)`.

### Pre-compilation mechanism in Julia 1.0

There was a major overhaul in the module loading system between Julia
0.6 and 1.0.  As a result, the "hack" supporting the PyJulia to load
PyCall stopped working.  For the implementation detail of the hack,
see: https://github.com/JuliaPy/pyjulia/tree/master/julia/fake-julia

For the update on this problem, see:
https://github.com/JuliaLang/julia/issues/28518

### <kbd>Ctrl-C</kbd> does not work / terminates the whole Python process

Currently, initializing PyJulia (e.g., by `from julia import Main`)
disables `KeyboardInterrupt` handling in the Python process.  If you
are using normal `python` interpreter, it means that canceling the
input by <kbd>Ctrl-C</kbd> does not work and repeatedly providing
<kbd>Ctrl-C</kbd> terminates the whole Python process with the error
message `WARNING: Force throwing a SIGINT`.  Using IPython 7.0 or
above is recommended to avoid such accidental shutdown.

It also means that there is no safe way to cancel long-running
computations or I/O at the moment.  Sending SIGINT with
<kbd>Ctrl-C</kbd> will terminate the whole Python process.

For the update on this problem, see:
https://github.com/JuliaPy/pyjulia/issues/211

### No threading support

PyJulia cannot be used in different threads since libjulia is not
thread safe.  However, you can
[use multiple threads within Julia](https://docs.julialang.org/en/v1.0/manual/parallel-computing/#Multi-Threading-(Experimental)-1).
For example, start IPython by `JULIA_NUM_THREADS=4 ipython` and then
run:

```julia
In [1]: %load_ext julia.magic
Initializing Julia interpreter. This may take some time...

In [2]: %%julia
   ...: a = zeros(10)
   ...: Threads.@threads for i = 1:10
   ...:     a[i] = Threads.threadid()
   ...: end
   ...: a
Out[3]: array([1., 1., 1., 2., 2., 2., 3., 3., 4., 4.])
```

### PyJulia does not release GIL

PyJulia does not release the Global Interpreter Lock (GIL) while
calling Julia functions since PyCall expects the GIL to be acquired
always.  It means that Python code and Julia code cannot run in
parallel.


Testing
-------

PyJulia can be tested by simply running [`tox`](http://tox.readthedocs.io):

```console
$ tox
```

The full syntax for invoking `tox` is

```shell
[PYJULIA_TEST_REBUILD=yes] [JULIA_EXE=<julia>] tox [options] [-- pytest options]
```

* `PYJULIA_TEST_REBUILD`: *Be careful using this environment
  variable!* When it is set to `yes`, your `PyCall.jl` installation
  will be rebuilt using the Python interpreter used for testing.  The
  test suite tries to build back to the original configuration but the
  precompilation would be in the stale state after the test.  Note
  also that it does not work if you unconditionally set `PYTHON`
  environment variable in your Julia startup file.

* `JULIA_EXE`: `julia` executable to be used for testing.

* Positional arguments after `--` are passed to `pytest`.

For example,

```console
$ PYJULIA_TEST_REBUILD=yes JULIA_EXE=~/julia/julia tox -e py37 -- -s
```

means to execute tests with

* PyJulia in shared-cache mode
* `julia` executable at `~/julia/julia`
* Python 3.7
* `pytest`'s capturing mode turned off
