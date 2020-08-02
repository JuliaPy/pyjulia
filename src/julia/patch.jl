try
    julia_py = ENV["_PYJULIA_JULIA_PY"]

    if Base.julia_cmd().exec[1] == julia_py
        @debug "Already monkey-patched. Skipping..." julia_py getpid()
    else
        @debug "Monkey-patching..." julia_py getpid()

        # Monkey patch `Base.package_slug`
        #
        # This is used for generating the set of precompilation cache paths
        # for PyJulia different to the standard Julia runtime.
        #
        # See also:
        # * Suggestion: Use different precompilation cache path for different
        #   system image -- https://github.com/JuliaLang/julia/pull/29914
        #
        if VERSION < v"1.4.0-DEV.389"
            Base.eval(
                Base,
                quote
                    function package_slug(uuid::UUID, p::Int = 5)
                        crc = _crc32c(uuid)
                        crc = _crc32c(unsafe_string(JLOptions().image_file), crc)
                        crc = _crc32c(unsafe_string(JLOptions().julia_bin), crc)
                        crc = _crc32c($julia_py, crc)
                        return slug(crc, p)
                    end
                end,
            )
        else
            Base.eval(Base, quote
                function package_slug(uuid::UUID, p::Int = 5)
                    crc = _crc32c(uuid)
                    crc = _crc32c($julia_py, crc)
                    return slug(crc, p)
                end
            end)
        end

        # Monkey patch `Base.julia_exename`.
        #
        # This is required for propagating the monkey patches to subprocesses.
        # This is important especially for the subprocesses used for
        # precompilation.
        #
        # See also:
        # * Request: Add an API for configuring julia_cmd --
        #   https://github.com/JuliaLang/julia/pull/30065
        #
        Base.eval(Base, quote
            julia_exename() = $julia_py
        end)
        @assert Base.julia_cmd().exec[1] == julia_py

        @debug "Successfully monkey-patched" julia_py getpid()
    end
catch err
    @error "Failed to monkey-patch `julia`" exception = (err, catch_backtrace()) getpid()
    rethrow()
end
