#!/usr/bin/env python3


import os
import sys

def force_reload():
    for name in (
        'test_regressions',
        'test_ytjd_corpus',
        'correlate'
        ):
        if name in sys.modules:
            del sys.modules[name]

    import correlatetestlib
    return correlatetestlib.preload_local_correlate()

correlate_dir = force_reload()
os.chdir(correlate_dir)

# ensure debug statements are off
os.system(sys.executable + " correlate/debug.py -c")


# unoptimized tests/regression.test.py unoptimized

python3 tests/regression.test.py -v | tail -1
echo

echo tests/ytjd.test.py unoptimized
echo -n "    "
python3 tests/ytjd.test.py -v | tail -1
echo

echo tests/regression.test.py optimized
echo -n "    "
python3 -O tests/regression.test.py -v | tail -1
echo

echo tests/ytjd.test.py optimized
echo -n "    "
python3 -O tests/ytjd.test.py -v | tail -1
echo

echo
python3 correlate/debug.py -c
echo

echo unoptimized tests/regression.test.py unoptimized
echo -n "    "
python3 tests/regression.test.py -v | tail -1
echo

echo tests/ytjd.test.py unoptimized
echo -n "    "
python3 tests/ytjd.test.py -v | tail -1
echo

echo tests/regression.test.py optimized
echo -n "    "
python3 -O tests/regression.test.py -v | tail -1
echo

echo tests/ytjd.test.py optimized
echo -n "    "
python3 -O tests/ytjd.test.py -v | tail -1
echo


echo done.
