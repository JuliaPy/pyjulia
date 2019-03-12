How it works
------------
PyJulia loads the `libjulia` library and executes the statements therein.
To convert the variables, the `PyCall` package is used. Python references
to Julia objects are reference counted by Python, and retained in the
`PyCall.pycall_gc` mapping on the Julia side (the mapping is removed
when reference count drops to zero, so that the Julia object may be freed).
