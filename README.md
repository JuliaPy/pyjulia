PyJulia
=======

[![Build Status](https://travis-ci.org/JuliaPy/pyjulia.svg?branch=master)](https://travis-ci.org/JuliaPy/pyjulia)
[![Build status](https://ci.appveyor.com/api/projects/status/github/JuliaPy/pyjulia?svg=true)](https://ci.appveyor.com/project/Keno/pyjulia)

Experimenting with developing a better interface to [Julia language](https://julialang.org/) that works with [Python](https://www.python.org/) 2 & 3 and Julia v0.6+.

to run the tests, execute from the toplevel directory

```shell
python -m unittest discover
```

**Note** You need to explicitly add julia to your `PATH`, an alias will not work.

`pyjulia` is tested against Python versions 2.7 and 3.5.  Older versions of Python (than 2.7)  are not supported.

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
To call Julia functions from python, first import the library

```python
import julia
```

then create a Julia object that makes a bridge to the Julia interpreter (assuming that `julia` is in your `PATH`)

```python
j = julia.Julia()
```

You can then call Julia functions from python, e.g.

```python
j.sind(90)
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
