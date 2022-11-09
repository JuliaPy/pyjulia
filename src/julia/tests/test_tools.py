import glob
import os
import platform
import sysconfig

import pytest

from julia.tools import _non_default_julia_warning_message, julia_py_executable

fake_user = "fa9a5150-8e17-11ea-3f8d-ff1e5ae4a251"
posix_user_sample_path = os.path.join(os.sep, "home", fake_user, ".local", "bin")
standard_sample_path = os.path.join(os.sep, "usr", "bin")


def get_path_mock_scheme(scheme):
    # We'll ignore the other alternate install scheme types and just handle "posix_user" and None (standard install).
    # We use sample scripts paths as reported by sysconfig.get_path("scripts","posix_user") and
    # sysconfig.get_path("scripts") on a Linux system.
    assert scheme in ("posix_user", None)
    if scheme is None:
        # standard
        return standard_sample_path
    else:
        # posix_user
        return posix_user_sample_path


def julia_py_with_command_extension():
    extension = ".cmd" if platform.system() == "Windows" else ""
    return "julia-py" + extension


def glob_mock(path=None):
    # we're only handling the case when the glob is ".../julia-py*" or nothing
    # if path is None then return empty list - this is indicator that we don't want to "find" any files matching a glob
    if path is None:
        return []
    else:
        return [os.path.join(os.path.dirname(path), julia_py_with_command_extension())]


def test_find_julia_py_executable_by_scheme(monkeypatch):
    # could extend this to test different kinds of scheme
    # right now we just fake the "posix_user" scheme and standard scheme, giving two paths to look in

    monkeypatch.setattr(sysconfig, "get_scheme_names", lambda: ("posix_user",))
    monkeypatch.setattr(
        sysconfig, "get_path", lambda x, scheme=None: get_path_mock_scheme(scheme)
    )
    monkeypatch.setattr(glob, "glob", glob_mock)

    jp = julia_py_executable()

    assert jp == os.path.join(posix_user_sample_path, julia_py_with_command_extension())


def test_find_julia_py_executable_standard(monkeypatch):
    # as though we only have standard install available, or didn't find julia-py in any alternate install location

    monkeypatch.setattr(sysconfig, "get_scheme_names", lambda: ())
    monkeypatch.setattr(
        sysconfig, "get_path", lambda x, scheme=None: get_path_mock_scheme(scheme)
    )
    monkeypatch.setattr(glob, "glob", glob_mock)

    jp = julia_py_executable()

    assert jp == os.path.join(standard_sample_path, julia_py_with_command_extension())


def test_find_julia_py_executable_not_found(monkeypatch):
    # look in posix_user and standard locations but don't find anything

    monkeypatch.setattr(sysconfig, "get_scheme_names", lambda: ("posix_user",))
    monkeypatch.setattr(
        sysconfig, "get_path", lambda x, scheme=None: get_path_mock_scheme(scheme)
    )
    monkeypatch.setattr(glob, "glob", lambda x: glob_mock())

    with pytest.raises(RuntimeError) as excinfo:
        julia_py_executable()

    assert "``julia-py`` executable is not found" in str(excinfo.value)


def test_non_default_julia_warning_message():
    msg = _non_default_julia_warning_message("julia1.5")
    assert "Julia(runtime='julia1.5')" in msg
