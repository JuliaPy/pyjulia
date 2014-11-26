pyjulia
=======

[![Build Status](https://travis-ci.org/JuliaLang/pyjulia.svg?branch=master)](https://travis-ci.org/JuliaLang/pyjulia)

Experimenting with developing a better interface to julia that works with Python 2 & 3.

to run the tests, execute from the toplevel directory

```shell
python -m unittest discover
```

**Note** You need to explicitly add julia to your PATH, an alias will not work.

Installation
------------
You will need to install PyCall in your existing Julia installation

```
Pkg.add("PyCall")
```

Your python installation must be able to call Julia.  If your installer
does not add the Julia binary directory to your PATH, you will have to
add it.


