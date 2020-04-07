#!/usr/bin/env python3
#
# correlate
# Copyright 2019-2020 by Larry Hastings
#
# Regression and smoke tests for correlate.
#
# Part of the "correlate" package:
# http://github.com/larryhastings/correlate

import itertools
import os.path
import sys

from correlate import *

original_print = print
def print(*a, sep=" "):
    s = sep.join(str(o) for o in a)
    original_print(f"    {s}".rstrip())

# my local pprint
import io
import pprint as _pprint
def pprint(name, o):
    s = io.StringIO()
    _pprint.pprint(o, stream=s)
    s = s.getvalue().rstrip()
    print(f"{name}:")
    for line in s.split("\n"):
        print("    " + line.rstrip())



def smoke_test(verbose):
    """
    The phrase "smoke test" is slang meaning "the simplest
    possible test".  As in, here's how you test an electrical
    applicance: plug it in, turn it on, and see if "the smoke"
    comes out.
    """

    c = Correlator()
    a, b = c.datasets

    a.set_keys("this this this Greg Greg".split(), "greg")
    a.set_keys("This is Carol I repeat this is Carol".split(), "carol")
    a.set_keys("This is Tony".split(), "tony")
    a.set_keys("This is Steve".split(), "steve")
    a.set_keys("blasdlkj alskdjwekj lkjaslkj".split(), "unmatched 1")
    a.set_keys("paosdpas oasidfjoas paosfdpsaod".split(), "unmatched 2")
    a.set("meredith", "meredith", weight=1)
    a.set("meredith", "meredith", weight=3)
    a.set("meredith", "meredith", weight=5)

    b = c.dataset_b
    b.set_keys("this this this Greg Greg".split(), "greg")
    b.set_keys("hey we found Carol this is a good idea I repeat this is Carol".split() , "carol")
    b.set_keys("Tony over here".split(), "tony")
    b.set_keys("This is Steve".split(), "steve")
    b.set_keys("no correlations found".split(), "unmatched 3")
    b.set("meredith", "meredith", weight=3)
    b.set("meredith", "meredith", weight=1)
    b.set("meredith", "meredith", weight=5)

    result = c.correlate()
    if verbose:
        pprint("matches", result.matches)
        pprint("unmatched a", result.unmatched_a)
        pprint("unmatched b", result.unmatched_b)
    assert len(result.matches) == 5
    for match in result.matches:
        assert match.value_a == match.value_b
    assert len(result.unmatched_a) == 2
    assert len(result.unmatched_b) == 1
    for value in itertools.chain(result.unmatched_a, result.unmatched_b):
        assert "unmatched" in value


def fuzzy_rounds_stress_test(verbose):
    """
    in each round of fuzzy keys, we use only the highest scoring match
    for each key.  but that means some keys could theoretically go unused.
    what they *should* do is stick around and get reused in the next round,
    if any.

    it gets worse! that unused key could also be present in the following round!
    and it could *still* not get used.  so the same key could stick around *twice,*
    with a second copy of that key waiting in the wings behind it.

    let's test it!

    dataset A has one value VA
    three keys map to it, all fuzzy, KA1, KA2, KA3.
    their scores are respectively 4, 2, 1.
    KA3 is mapped to VA twice!  the first time with weight 2, the second with weight 1.
    KA3 is mapped to VA three times!  the weights for these mappings: 4, 2, 1.
    (but we'll add them in the order 2 4 1 so we check that weights are stored correctly)

    dataset B has one value VB
    one key maps to it five times!  this is key KB1 with score 1 and weights 5 4 3 2 1.

    we'll add a lowercase letter to representing each mapping: KB1a, KB1b, KB1c, KB1d, KB1e.  and KA3a and KA3b.
    in the first round, KA1 matches KB1a.  KA2 and KA3a go unused and stick around.
    in the second round, KA2 matches KB1b.   KA3a is still unused, and KA3b is unused too.
    in the third round, KA3a matches KB1c, leaving KA3b unused.
    in the fourth round, KA3b matches KB1d, leaving KB1e.
    in the fifth round, there are no dataset_a keys left so we're done.  KB1e goes unmatched.
    """

    va = "VA"
    vb = "VB"

    class FauxyKey(FuzzyKey):
        def __init__(self, name, score):
            self.name = name
            self.score = score

        def compare(self, other):
            return self.score

        def __repr__(self):
            return f"<FauxyKey {self.name!r} {self.score}>"

    c = Correlator()
    a, b = c.datasets
    a.set(FauxyKey("KA1", 1), va)
    a.set(FauxyKey("KA2", 0.5), va)
    ka3 = FauxyKey("KA3", 0.2)
    a.set(ka3, va, weight=2)
    a.set(ka3, va, weight=3)
    a.set(ka3, va, weight=1)

    kb1 = FauxyKey("KB1", 1)
    for weight in (4, 1, 3, 5, 2, 1):
        b.set(kb1, vb, weight=weight)

    result = c.correlate(key_reuse_penalty_factor=0.5)
    if verbose:
        pprint("matches", result.matches)
    assert len(result.matches) == 1
    score = result.matches[0].score
    expected_score = 6.884943181818182
    assert score == expected_score, f"{score=} {expected_score=}"



def fuzzy_matches_stress_test(verbose):
    """
    another wrinkle in fuzzy key scoring!

    the setup:
      * dataset_a: fuzzy keys fka1 fka2
      * dataset_b: fuzzy keys fkbH (high scoring) and fkbL (low scoring)
      * fka1->fkbH == fka2->fkbH
      * fka1->fkbL <  fka2->fkbL

    the problem: how do we ensure that correlate picks fka2->fkbL?
      it can only do that if it previously picked fka1->fkbH.  but
      it doesn't look forward!

    answer: when there are multiple fuzzy key matches with the same top
      score, wherever we are in looping over fuzzy_matches, and more than
      one of those include the same key, you must try all possible combinations.
      think of it as little alternate timelines: you need to try each choice
      and keep the one with the highest *final* score.
        * in this example, you must try *both* fka1->fkbH *and* fka2->fkbH.
        * all possible systems of matches that have keys in common must be tried.
          if you had:
            * A1->B1
            * A2->B1
            * A1->B2
            * A2->B3
            * A3->B4
          you must try each of the first four combinations.  the last one, A3->B4,
          has no keys in common with any of the other attempts.  so we'll get to
          keep that one regardless.
            * in fact, it'll be cheaper if you commit A3->B4 first, before doing
              the alternate timelines check.  so: sort by "len(key matches group)"
              and consume smaller numbers first.
            * you CAN have to do this multiple times!  in this example, we could
              then have fka3 and fka4 and fkbH2 and fkbL2, etc etc etc.
        * note that this does not extend past the current loop over fuzzy_matches!
          you *don't* need to change the hopper to accommodate this, that part *doesn't*
          change.  you only have to compute it using the current list of fuzzy_matches.
          (it's because round N is a strict subset of round N-1, and for the
          purposes of this stage of scoring you ignore the weights.)

    using itertools.permutations below ensures that we add all keys in
    all orders.  when I wrote the test, I got two different results:
    two of the four correlations scored the match as 2.25, which is correct,
    and the other half scored it as 1.875--which is wrong!
    """
    class MaxKey(FuzzyKey):
        def __init__(self, score):
            self.score = score

        def compare(self, other):
            return max(self.score, other.score)

        def __repr__(self):
            return f"<MaxKey {self.score}>"

    scores = []
    for a_keys in itertools.permutations([MaxKey(0.25), MaxKey(0.5)]):
        for b_keys in itertools.permutations([MaxKey(1), MaxKey(0)]):
            c = Correlator()
            a, b = c.datasets
            for a_key in a_keys:
                a.set(a_key, "VA")
            for b_key in b_keys:
                b.set(b_key, "VB")
            result = c.correlate()
            match = result.matches[0]
            scores.append(match.score)
            if verbose:
                pprint("a_keys", a_keys)
                pprint("b_keys", b_keys)
                pprint("matches", result.matches[0])
                print()
    correct_score = 2.25
    for score in scores:
        assert score == correct_score, f"{score=} != {correct_score=}, {scores=}"


def match_boiler_test(verbose):
    def test(matches, verbose):
        if verbose:
            pprint("matches", matches)
        boiler = MatchBoiler()
        boiler.matches = list(matches)
        result, seen_a, seen_b = boiler()
        if verbose:
            pprint("result", result)
        cumulative_score = sum((item.score for item in result))
        if verbose:
            print(f"{cumulative_score=}")
            print()
        return cumulative_score, result, seen_a, seen_b

    def permuted_matches_test(name, matches, verbose):
        results = []
        _verbose = verbose
        permutations = list(itertools.permutations(matches))
        for i, permutation in enumerate(permutations, 1):
            if verbose:
                print(f"{name} test {i}/{len(permutations)}")
            result = test(permutation, _verbose)
            results.append(result)
            if _verbose:
                _verbose -= 1

        first_result = results[0]
        assert all(result == first_result for result in results), f"all results should be the same!  {results=}"
        if verbose:
            print()


    permuted_matches_test("three items",
        [
            CorrelatorMatch("a1", "b1", 1),
            CorrelatorMatch("a2", "b2", 2),
            CorrelatorMatch("a3", "b3", 3),
        ],
        verbose)

    permuted_matches_test("five items",
        [
            CorrelatorMatch("a1", "b1", 5),
            CorrelatorMatch("a1", "b2", 5),
            CorrelatorMatch("a2", "b1", 5),
            CorrelatorMatch("a3", "b2", 4),
            CorrelatorMatch("a2", "b3", 3),
        ],
        verbose)


##
##
##
##
##
##

tests = {name[:-5] : value for name, value in globals().items() if name.endswith("_test") and callable(value)}

def usage(error=None):
    print = original_print
    if error:
        print(f"Error: {error}")
        print()
    print(f"usage: {os.path.basename(sys.argv[0])} [-v|--verbose] [<test_name> [<test2_name> ...]]")
    print()
    print("Runs one or more discrete regression / smoke tests.")
    print()
    print("You can optionally specify which tests you want run.  Current tests:")
    for test in tests:
        print(f"    {test}")
    print()
    print("-v or --verbose turns on verbose output.")
    sys.exit(0)


def main(argv):

    verbose = 0
    tests_to_run = set()

    while argv and argv[0].startswith("-"):
        arg = argv.pop(0)
        if arg in {'-v', '--verbose'}:
            verbose += 1
            continue
        usage(f"unknown flag {arg}")

    tests_to_run.update(set(argv))
    print_header = False

    tests_run = 0
    successes = 0
    for name, fn in tests.items():
        if tests_to_run and name not in tests_to_run:
            continue

        tests_run += 1
        if verbose:
            if print_header:
                original_print()
                original_print("-" * 79)
                original_print()
            original_print(f"{name} test:")
            original_print()
            print_header = True
        try:
            fn(verbose)
            successes += 1
        except AssertionError as e:
            print(repr(e))
    if successes == tests_run:
        original_print("All tests passed.")
    else:
        failures = tests_run - successes
        def spell_tests(i):
            test = "test" if i == 1 else "tests"
            return f"{i} {test}"

        original_print(f"{failures} out of {spell_tests(tests_run)} failed.")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
