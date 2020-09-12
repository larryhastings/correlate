#!/bin/sh
#
# This is designed to be run from the "correlate" directory,
# not from the "tests" directory.

echo
python3 correlate/debug.py -u
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
