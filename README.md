PyJulia
=======

[![Stable documentation](https://img.shields.io/badge/docs-stable-blue.svg)](https://pyjulia.readthedocs.io/en/stable/)
[![Latest documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://pyjulia.readthedocs.io/en/latest/)
[![Main workflow](https://github.com/JuliaPy/pyjulia/workflows/Main%20workflow/badge.svg)](https://github.com/JuliaPy/pyjulia/actions?query=workflow%3A%22Main+workflow%22)
[![DOI](https://zenodo.org/badge/14576985.svg)](https://zenodo.org/badge/latestdoi/14576985)

Experimenting with developing a better interface to [Julia language](https://julialang.org/) that works with [Python](https://www.python.org/) 2 & 3 and Julia v1.0+.

Quick usage
-----------

```console
$ python3 -m pip install julia    # install PyJulia
...                               # you may need `--user` after `install`

$ python3
>>> import julia
>>> julia.install()               # install PyCall.jl etc.
>>> from julia import Base        # short demo
>>> Base.sind(90)
1.0
```

See more in the [documentation](https://pyjulia.readthedocs.io).
