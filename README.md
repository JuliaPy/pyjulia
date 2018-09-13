PyJulia
=======

[![Build Status](https://travis-ci.org/JuliaPy/pyjulia.svg?branch=master)](https://travis-ci.org/JuliaPy/pyjulia)
[![Build status](https://ci.appveyor.com/api/projects/status/github/JuliaPy/pyjulia?svg=true)](https://ci.appveyor.com/project/Keno/pyjulia)

Experimenting with developing a better interface to [Julia language](https://julialang.org/) that works with [Python](https://www.python.org/) 2 & 3 and Julia v0.6+.

to run the tests, execute from the toplevel directory

```shell
tox
```

See [Testing](#testing) below for details.

**Note** You need to explicitly add julia to your `PATH`, an alias will not work.

`pyjulia` is tested against Python versions 2.7, 3.6, and 3.7.  Older versions of Python (than 2.7)  are not supported.

Installation of PyCall
------------------------
PyCall needs to be associated with the python executable with which you will call pyjulia.  To find the executable location from within a python interpret
```python
>>> import os
>>> import sys
>>> os.path.dirname(sys.executable)
'C:\\Anaconda3'
```

Follow the [PyCall](https://github.com/JuliaPy/PyPlot.jl#automated-matplotlib-installation) instructions within julia.  To install and then associate PyCall with the appropriate python interpret (such as that found in `C:\\bin\\Anaconda3` above,

```julia
Pkg.add("PyCall")
ENV["PYTHON"] = "C:\\Anaconda3" #Or the location of your python interpreter
Pkg.build("PyCall")
```
If you do not specify `ENV["PYTHON"]` and then build `PyCall`, then the python environment is assumed to be the Conda installed within Julia.

Installation of pyjulia
------------------------
Your python installation must be able to call Julia.  If your installer
does not add the Julia binary directory to your `PATH`, you will have to
add it.  To find the executable of Julia from the REPL, use `JULIA_HOME`.

Then finally you have to install pyjulia.

To get released versions you can use:

```
pip install julia
```

You may clone it directly to your home directory.

```
git clone https://github.com/JuliaPy/pyjulia

```
then inside the pyjulia directory you need to run the python setup file

```
[sudo] pip install [-e] .
```

The `-e` flag makes a development install meaning that any change to pyjulia
source tree will take effect at next python interpreter restart without having
to reissue an install command.

`pyjulia` is known to work with `PyCall.jl` ≥ `v0.7.2`.

If you run into problems using `pyjulia`, first check the version of `PyCall.jl` you have installed by running `Pkg.installed("PyCall")`.

Usage
-----

`pyjulia` provides a high-level interface which assumes a "normal"
setup (e.g., `julia` is in your `PATH`) and a low-level interface
which can be used in a customized setup.

### High-level interface

To call a Julia function in a Julia module, import the Julia module
(say `Base`) with:

```python
from julia import Base
```

and then call Julia functions in `Base` from python, e.g.,

```python
Base.sind(90)
```

Other variants of Python import syntax also work:

```python
import julia.Base
from julia.Base import LinAlg   # import a submodule
from julia.Base import sin      # import a function from a module
```

The global namespace of Julia's interpreter can be accessed via a
special module `julia.Main`:

```python
from julia import Main
```

You can set names in this module to send Python values to Julia:

```python
Main.xs = [1, 2, 3]
```

which allows it to be accessed directly from Julia code, e.g., it can
be evaluated at Julia side using Julia syntax:

```python
Main.eval("sin.(xs)")
```

### Low-level interface

If you need a custom setup for `pyjulia`, it must be done *before*
importing any Julia modules.  For example, to use the Julia
executable named `custom_julia`, run:

```python
from julia import Julia
jl = julia.Julia(runtime="custom_julia")
```

You can then use, e.g.,

```python
from julia import Base
```


How it works
------------
PyJulia loads the `libjulia` library and executes the statements therein.
To convert the variables, the `PyCall` package is used. Python references
to Julia objects are reference counted by Python, and retained in the
`PyCall.pycall_gc` mapping on the Julia side (the mapping is removed
when reference count drops to zero, so that the Julia object may be freed).



Limitations
------------

Not all valid Julia identifiers are valid Python identifiers.  Unicode identifiers are invalid in Python 2.7 and so `pyjulia` cannot call or access Julia methods/variables with names that are not ASCII only.  Additionally, it is a common idiom in Julia to append a `!` character to methods which mutate their arguments.  These method names are invalid Python identifers.  `pyjulia` renames these methods by subsituting `!` with `_b`.  For example, the Julia method `sum!` can be called in `pyjulia` using `sum_b(...)`.


Testing
-------

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

```shell
PYJULIA_TEST_REBUILD=yes JULIA_EXE=~/julia/julia tox -e py37 -- -s
```

means to execute tests with

* `pyjulia` in shared-cache mode
* `julia` executable at `~/julia/julia`
* Python 3.7
* `pytest`'s capturing mode turned off
