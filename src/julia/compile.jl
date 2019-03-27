script, output = ARGS

using Pkg
Pkg.activate(".")
Pkg.add("MacroTools")
Pkg.add("PyCall")
Pkg.activate()

using PackageCompiler
sysout, _curr_syso = compile_incremental("Project.toml", script)

cp(sysout, output, force=true)
