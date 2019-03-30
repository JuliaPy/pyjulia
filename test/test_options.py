from julia.options import JuliaOptions, options_docs


def parse_options_docs(docs):
    optdefs = {}
    for line in docs.splitlines():
        if line.startswith(" ") or not line:
            continue

        name, domain = line.split(":", 1)
        assert name not in optdefs
        optdefs[name] = {"domain": eval(domain, {})}
    return optdefs


def test_options_docs():
    """
    Ensure that `JuliaOptions` and `JuliaOptions.__doc__` agree.
    """

    optdefs = parse_options_docs(options_docs)
    for desc in JuliaOptions.supported_options():
        odef = optdefs.pop(desc.name)
        assert odef["domain"] == desc._domain()
    assert not optdefs
