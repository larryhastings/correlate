#!/usr/bin/env python3
#
# correlate debug preprocessor
# Copyright 2020 by Larry Hastings
#
# Rewrites ./__init__.py to turn on/off or toggle debug statements.
# Any line that ends with the six characters "#debug" is a "debug" statement;
# this script will add or remove comment characters from every debug statement.
#
# If run without arguments, this script will find the first debug statement
# and examine it:
#     * If the debug statement line starts with '#',
#       this script will will uncomment all debug statements.
#
#     * If the debug statement line does not start with a '#',
#       this script will will comment out all debug statements.
#
# The script is smart; it will remove all leading #'s when uncommenting,
# and will not add an additional # if there already is one when commenting.
#
# Future expansion: make an explicit command-line flag that lets you
# explicitly specify "comment" or "uncomment" debug statements.

import os.path
import sys


def usage():
    print("""
usage: debug.py [-c|--comment|-u|--uncomment]

either adds or removes comments from debug statements in ./__init__.py.
(looks in the same directory as debug.py, not in your current directory.)

-c or --comment tells debug.py to comment out debug statements.
-u or --uncomment tells debug.py to uncomment debug statements.

if no command-line argument is specified, debug.py examines the first
debug statement encountered in ./__init__.py.  if the line is commented-out,
debug.py acts as if -u was specified.  if the line is uncommented,
debug.py acts as if -c was specified.
""".strip())
    sys.exit(0)

argv0dir = os.path.dirname(sys.argv[0])
correlate = os.path.join(argv0dir, "__init__.py")

undecided = object()

commenting = undecided

if not len(sys.argv) < 3:
    usage()

if len(sys.argv) == 2:
    if sys.argv[1] in ("-c", "--comment"):
        commenting = True
    elif sys.argv[1] in ("-u", "--uncomment"):
        commenting = False
    else:
        usage()


lines = []
changes = 0
with open(correlate, "rt") as f:
    for line in f.read().split("\n"):
        line = line.rstrip()
        if not line.endswith("#debug"):
            lines.append(line)
            continue

        ws = []
        # first, preserve but split off leading whitespace
        for c in line:
            if c.isspace():
                ws.append(c)
                continue
            break
        ws = "".join(ws)
        line = line[len(ws):]

        if commenting == undecided:
            commenting = not line.startswith('#')

        if commenting:
            # commenting
            if not line.startswith("#"):
                line = "# " + line
                changes += 1
        else:
            # uncommenting
            if line.startswith("#"):
                changes += 1
                while line.startswith("#"):
                    line = line[1:].lstrip()
        lines.append(ws + line)

# force text to end with a newline
if lines[-1]:
    lines.append("")
text = "\n".join(lines)

with open(correlate, "wt") as f:
    f.write(text)

plural = "s" if changes != 1 else ""
operation = "commented out" if commenting else "uncommented"

sys.exit(f"{changes} debug statement{plural} {operation}.")