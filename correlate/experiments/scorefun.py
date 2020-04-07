#!/usr/bin/env python3
#
# correlate
# Copyright 2019-2020 by Larry Hastings
#
# Experiments with alternate approaches to scoring fuzzy matches.
#
# Part of the "correlate" package:
# http://github.com/larryhastings/correlate


import textwrap
import io
import pprint

def clip(f):
    return f"{f:.10f}".rstrip("0")

def dump(array):
    clipped = [clip(f) for f in array]
    joined = ", ".join(clipped)
    print(f"    [{joined}]")
    # print(textwrap.indent(s.getvalue(), "    ").rstrip())
    total = sum(array)
    print(f"    total={clip(total)}")
    average = clip(total / len(array))
    print(f"    {average=!s}")
    print()

def test(array):
    # combined_weight = ((weight_a * weight_b) * round_factor) / (len_weights_a * len_weights_b)
    # let's assume round factor is 1 for everybody
    # and we'll just consider one of the two keys
    print("-" * 80)
    print("original scores:")
    dump(array)

    divisor = len(array) ** 2
    print(f"score divided by number of hits squared ({divisor}):")
    dump([score / divisor for score in array])

    divisor = sum(array) ** 2
    print(f"score divided by the sum of this key's scores squared ({clip(divisor)}):")
    dump([score / divisor for score in array])

    print(f"score**2 divided by the sum of this key's scores squared ({clip(divisor)}):")
    dump([(score * score) / divisor for score in array])

    print(f"score**3 divided by the sum of this key's scores squared ({clip(divisor)}):")
    dump([(score ** 3) / divisor for score in array])

test([0.2, 0.6, 0.3, 0.35])
test([0.000000001])
test([0.0001, 0.000000001, 0.000000001])

