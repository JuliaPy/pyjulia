from __future__ import absolute_import, print_function

import os
import subprocess
import sys

is_linux = sys.platform.startswith("linux")
is_windows = os.name == "nt"
is_apple = sys.platform == "darwin"


def _execprog_os(cmd):
    os.execvp(cmd[0], cmd)


def _execprog_subprocess(cmd):
    sys.exit(subprocess.call(cmd))


if is_windows:
    # https://bugs.python.org/issue19124
    execprog = _execprog_subprocess
else:
    execprog = _execprog_os
