module _PyJuliaHelper

using PyCall
using PyCall: pyeval_, Py_eval_input, Py_file_input
using MacroTools
using MacroTools: isexpr

if VERSION < v"0.7-"
nameof(m::Module) = ccall(:jl_module_name, Ref{Symbol}, (Any,), m)

parentmodule(m::Module) = ccall(:jl_module_parent, Ref{Module}, (Any,), m)

function fullname(m::Module)
    mn = nameof(m)
    if m === Main || m === Base || m === Core
        return (mn,)
    end
    mp = parentmodule(m)
    if mp === m
        return (mn,)
    end
    return (fullname(mp)..., mn)
end
end  # if

"""
    fullnamestr(m)

# Examples
```jldoctest
julia> fullnamestr(Base.Enums)
"Base.Enums"
```
"""
fullnamestr(m) = join(fullname(m), ".")

isdefinedstr(parent, member) = isdefined(parent, Symbol(member))

if VERSION >= v"0.7-"
    import REPL

    function completions(str, pos)
        ret, ran, should_complete = REPL.completions(str, pos)
        return (
            map(REPL.completion_text, ret),
            (first(ran), last(ran)),
            should_complete,
        )
    end
end


macro prepare_for_pyjulia_call(ex)
    
    # f(x) returns transformed expression x and whether to recurse 
    # into the new expression
    function walk(f, x)
        (fx, recurse) = f(x)
        MacroTools.walk(fx, (recurse ? (x -> walk(f,x)) : identity), identity)
    end
    
    locals = gensym("locals")
    globals = gensym("globals")
    
    function make_pyeval(expr, options...)
        code = string(expr)
        T = length(options) == 1 && 'o' in options[1] ? PyObject : PyAny
        input_type = '\n' in code ? Py_file_input : Py_eval_input
        :($convert($T, $pyeval_($code, $(Expr(:$,globals)), $(Expr(:$,locals)), $input_type)))
    end
        
    ex = walk(ex) do x
        if isexpr(x, :$)
            if isexpr(x.args[1], :$)
                x.args[1], false
            else
                make_pyeval(x.args[1]), false
            end
        elseif isexpr(x, :macrocall) && x.args[1]==Symbol("@py_str")
            make_pyeval(x.args[3:end]...), false
        else
            x, true
        end 
    end
    esc(quote
        $pyfunction(($globals,$locals) -> (@eval Main $ex), $PyObject, $PyObject)
    end)
end


module IOPiper

const orig_stdin  = Ref{IO}()
const orig_stdout = Ref{IO}()
const orig_stderr = Ref{IO}()

function __init__()
@static if VERSION < v"0.7-"
    orig_stdin[]  = STDIN
    orig_stdout[] = STDOUT
    orig_stderr[] = STDERR
else
    orig_stdin[]  = stdin
    orig_stdout[] = stdout
    orig_stderr[] = stderr
end
end

"""
    num_utf8_trailing(d::Vector{UInt8})

If `d` ends with an incomplete UTF8-encoded character, return the number of trailing incomplete bytes.
Otherwise, return `0`.

Taken from IJulia.jl.
"""
function num_utf8_trailing(d::Vector{UInt8})
    i = length(d)
    # find last non-continuation byte in d:
    while i >= 1 && ((d[i] & 0xc0) == 0x80)
        i -= 1
    end
    i < 1 && return 0
    c = d[i]
    # compute number of expected UTF-8 bytes starting at i:
    n = c <= 0x7f ? 1 : c < 0xe0 ? 2 : c < 0xf0 ? 3 : 4
    nend = length(d) + 1 - i # num bytes from i to end
    return nend == n ? 0 : nend
end

function pipe_stream(sender::IO, receiver, buf::IO = IOBuffer())
    try
        while !eof(sender)
            nb = bytesavailable(sender)
            write(buf, read(sender, nb))

            # Taken from IJulia.send_stream:
            d = take!(buf)
            n = num_utf8_trailing(d)
            dextra = d[end-(n-1):end]
            resize!(d, length(d) - n)
            s = String(copy(d))

            write(buf, dextra)
            receiver(s)  # check isvalid(String, s)?
        end
    catch e
        if !isa(e, InterruptException)
            rethrow()
        end
        pipe_stream(sender, receiver, buf)
    end
end

const read_stdout = Ref{Base.PipeEndpoint}()
const read_stderr = Ref{Base.PipeEndpoint}()

function pipe_std_outputs(out_receiver, err_receiver)
    global readout_task
    global readerr_task
    read_stdout[], = redirect_stdout()
    readout_task = @async pipe_stream(read_stdout[], out_receiver)
    read_stderr[], = redirect_stderr()
    readerr_task = @async pipe_stream(read_stderr[], err_receiver)
end

end  # module

end  # module
