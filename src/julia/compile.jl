compiler_env, script, output, base_sysimage = ARGS

if VERSION < v"0.7-"
    error("Unsupported Julia version $VERSION")
end

const Pkg =
    Base.require(Base.PkgId(Base.UUID("44cfe95a-1eb2-52ea-b672-e2afdf69b78f"), "Pkg"))

Pkg.activate(compiler_env)
@info "Loading PackageCompiler..."
using PackageCompiler

@info "Installing PyCall..."
Pkg.activate(".")
Pkg.add([
    Pkg.PackageSpec(
        name = "PyCall",
        uuid = "438e738f-606a-5dbb-bf0a-cddfbfd45ab0",
    ),
])

if VERSION >= v"1.5-"
    mktempdir() do dir
        tmpimg = joinpath(dir, basename(output))
        @info "Compiling a temporary system image without `PyCall`..."
        create_sysimage(
            Symbol[];
            sysimage_path = tmpimg,
            project = ".",
            base_sysimage = isempty(base_sysimage) ? nothing : base_sysimage,
        )
        @info "Compiling system image..."
        create_sysimage(
            [:PyCall];
            sysimage_path = output,
            project = ".",
            precompile_execution_file = script,
            base_sysimage = tmpimg,
        )
    end
else
    @info "Compiling system image..."
    create_sysimage(
        [:PyCall],
        sysimage_path = output,
        project = ".",
        precompile_execution_file = script,
        base_sysimage = isempty(base_sysimage) ? nothing : base_sysimage,
    )
end

@info "System image is created at $output"

# Notes on two-stage system image monkey-patching for Julia 1.5
#
# Naive `@eval Base`-based monkey-patching stopped working as of Julia 1.5
# presumably because @eval-ing to another module during precompilation now
# throws an error: https://github.com/JuliaLang/julia/pull/35410
#
# We workaround this by creating the system image in two stages:
#
#   1.   The first stage is monkey-patching as done before but without
#       PyCall. This way, we don't get the error because julia does not
#       try to precompile any packages.
#
#   2.   The second stage is the inclusion of PyCall. At this point, we are
#       in a monkey-patched system image. So, it's possible to precompile
#       PyCall now.
#
# Note that even importing PackageCompiler.jl itself inside julia-py is
# problematic because (normally) it has to be precompiled. We avoid this
# problem by running PackageCompiler.jl under --compiled-modules=no. This is
# safe to do thanks to PackageCompiler.do_ensurecompiled
# (https://github.com/JuliaLang/PackageCompiler.jl/blob/3f0f4d882c560c4e4ccc6ab9a8b51ced380bb0d5/src/PackageCompiler.jl#L181-L188)
# using a custom function PackageCompiler.get_julia_cmd
# (https://github.com/JuliaLang/PackageCompiler.jl/blob/3f0f4d882c560c4e4ccc6ab9a8b51ced380bb0d5/src/PackageCompiler.jl#L113-L116)
# (instead of Base.julia_cmd) and ignores --compiled-modules=no of the current
# process.
