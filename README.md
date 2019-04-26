PyJulia
=======

[![Stable documentation](https://img.shields.io/badge/docs-stable-blue.svg)](https://pyjulia.readthedocs.io/en/stable/)
[![Latest documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://pyjulia.readthedocs.io/en/latest/)
[![Build Status](https://travis-ci.org/JuliaPy/pyjulia.svg?branch=master)](https://travis-ci.org/JuliaPy/pyjulia)
[![Build status](https://ci.appveyor.com/api/projects/status/github/JuliaPy/pyjulia?svg=true)](https://ci.appveyor.com/project/Keno/pyjulia)

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
