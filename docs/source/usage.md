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

```none
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

Any `$var` or `$(var)` expressions that appear in the Julia code (except in
comments or string literals) are evaluated in Python and passed to Julia. Use
`$$var` to insert a literal `$var` in Julia code.

```none
In [3]: foo = [[1,2],[3,4]]

In [4]: %julia $foo .+ 1

Out[4]: 
array([[2, 3],
       [4, 5]], dtype=int64)
       
In [22]: %%julia
   ...: bar=3
   ...: :($$bar)
   
Out[22]: 3

```

Variables are automatically converted between equivalent Python/Julia types (should they exist) using PyCall. Note below that `1`, `x`, and the tuple itself are converted to Julia `Int64`, `String`, and `Tuple`, respectively, although the function `abs` and the result of `typeof` are not.

```none
In [6]: %julia typeof($(1,"x",abs))

Out[6]: <PyCall.jlwrap Tuple{Int64,String,PyObject}>
```

#### IPython configuration

PyJulia-IPython integration can be configured via IPython's
configuration system.  For the non-default behaviors, add the
following lines in, e.g.,
``~/.ipython/profile_default/ipython_config.py`` (see
[Introduction to IPython configuration](https://ipython.readthedocs.io/en/stable/config/intro.html)).

To disable code completion in ``%julia`` and ``%%julia`` magics, use

```python
c.JuliaMagics.completion = False  # default: True
```

To disable code highlighting in ``%%julia`` magic for terminal
(non-Jupyter) IPython, use

```python
c.JuliaMagics.highlight = False  # default: True
```

To enable [Revise.jl](https://github.com/timholy/Revise.jl)
automatically, use

```python
c.JuliaMagics.revise = True  # default: False
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
