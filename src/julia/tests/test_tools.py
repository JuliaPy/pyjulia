import pytest
import platform
import sysconfig
import os
import glob

from julia.tools import julia_py_executable


def julia_py_with_command_extension():
    extension = ".cmd" if platform.system() == "Windows" else ""
    return "julia-py" + extension


def glob_mock(path):
    # we're only handling the case when the glob is ".../julia-py*" or just "julia-py*"
    # if dirname(path) is empty then return empty list - this is indicator that we shouldn't "find" any files matching the glob
    return [] if os.path.dirname(path) == "" else [os.path.join(os.path.dirname(path), julia_py_with_command_extension())]


def test_find_julia_py_executable_by_scheme(monkeypatch):
    # could extend this to test different kinds of scheme
    # right now we just fake the "posix_user" scheme and don't use the rest of get_path_mock_scheme()
    fake_user = "fa9a5150-8e17-11ea-3f8d-ff1e5ae4a251"
    fake_folder = "ce410603-12fa-42a2-9a24-e44cd94f6968"

    def get_path_mock_scheme(scheme_match, scheme):
        # sample scripts paths for each scheme type as reported by sysconfig.get_path("scripts",scheme) on a Linux system
        # sysconfig.get_path("scripts","nt_user") is going to have a different form on Windows, something like "\user\xyz\appdata\..."
        if scheme == scheme_match:
            if scheme == "posix_user" or scheme == "osx_framework_user":
                return os.path.join(os.path.abspath("home"), fake_user, ".local", "bin")
            elif scheme == "posix_prefix" or scheme == "posix_home":
                return os.path.join(os.path.abspath("usr"), "bin")
            elif scheme == "nt":
                return os.path.join(os.path.abspath("usr"), "Scripts")
            elif scheme == "nt_user":
                return os.path.join(os.path.abspath("home"), fake_user, ".local", "Python38", "Scripts")
            else:
                return os.path.join(os.path.abspath("tmp"), fake_folder)
        else:
            return ""

    monkeypatch.setattr("sysconfig.get_path", lambda x, scheme = None: get_path_mock_scheme("posix_user", scheme))
    monkeypatch.setattr("glob.glob", lambda x: glob_mock(x))

    jp = julia_py_executable()

    assert jp == os.path.join(os.path.abspath("home"), fake_user, ".local", "bin", julia_py_with_command_extension())


def test_find_julia_py_executable_standard(monkeypatch):

    def get_path_mock_standard(scheme):
        return os.path.join(os.path.abspath("usr"), "bin") if scheme == None else ""

    monkeypatch.setattr("sysconfig.get_path", lambda x, scheme = None: get_path_mock_standard(scheme))
    monkeypatch.setattr("glob.glob", lambda x: glob_mock(x))

    jp = julia_py_executable()

    assert jp == os.path.join(os.path.abspath("usr"), "bin", julia_py_with_command_extension())


def test_find_julia_py_executable_not_found(monkeypatch):

    def get_path_mock_not_found():
        return ""

    monkeypatch.setattr("sysconfig.get_path", lambda x, scheme = None: get_path_mock_not_found())
    monkeypatch.setattr("glob.glob", lambda x: glob_mock(x))

    try:
        julia_py_executable()
        notfound = False
    except RuntimeError as exc:
        notfound = "``julia-py`` executable is not found" in exc.args[0]

    assert notfound
