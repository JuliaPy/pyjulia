Installation
------------

**Note:** If you are using Python installed with Ubuntu or `conda`,
PyJulia may not work with Julia ≥ 0.7.  For workarounds, see
[Troubleshooting](troubleshooting.md).  Same caution applies to
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

See [Testing](testing.md) for how to run tests.
