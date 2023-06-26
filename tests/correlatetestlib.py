#!/usr/bin/env python3

import pathlib
import sys


def preload_local_correlate():
    """
    Pre-load the local "correlate" module, to preclude finding
    an already-installed one on the path.
    """

    argv_0 = pathlib.Path(sys.argv[0])
    correlate_dir = argv_0.resolve().parent
    while True:
        correlate_init = correlate_dir / "correlate" / "__init__.py"
        if correlate_init.is_file():
            break
        correlate_dir = correlate_dir.parent

    # this almost certainly *is* a git checkout
    # ... but that's not required, so don't assert it.
    # assert (correlate_dir / ".git" / "config").is_file()

    if correlate_dir not in sys.path:
        sys.path.insert(1, str(correlate_dir))

    import correlate
    assert correlate.__file__.startswith(str(correlate_dir))
    return correlate_dir
