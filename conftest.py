import sys

if sys.version_info[0] < 3:
    collect_ignore_glob = [
        "**/monkeypatch_completer.py",
        "**/monkeypatch_interactiveshell.py",
    ]
    # Theses files are ignored as import fails at collection phase.
