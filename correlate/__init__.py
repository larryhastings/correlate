#!/usr/bin/env python3
#
# correlate
# Copyright 2019-2020 by Larry Hastings
#
# Correlates two sets of things
# by scanning over data sets,
# pairing up values based on matching keys,
# and doing the best it can.
#
# Part of the "correlate" package:
# http://github.com/larryhastings/correlate

"""
Correlates two sets of data by matching unique or fuzzy
keys from both datasets, with tunable heuristics.
"""

# TODO:
#   * doc: match boiler is gale-shipley with operations reordered/unrolled
#
#   * doc: new fuzzy boiler approach
#       * move streamlined below rounds, because rounds are mostly conceptual at this point
#
#   * possible new ranking approach
#       * take the highest-scoring (pre-ranking) match, then assume that the
#         two rankings for a and b are absolute and should be the same.
#         so if the top scoring match has "a" value ranked 32 and "b" value ranked 75,
#         then assume all ranks in "b" should be the rank in "a" + (75 - 32=) 43
#         in other words, this is the same as absolute ranking, but with a delta.
#           * maybe also try this delta with relative ranking?
#
#   * a re-think on ordering
#       * it'd be nice to make ordering not so strictly arithmetic,
#         and more just about relative ordering of items.
#         e.g. if in dataset_a, A comes before B comes before C,
#             and in dataset_b, D comes before E comes before F,
#             if you match B to E,
#             you should resist matching A to F or C to D.
#         but how do you do that!?

import builtins
from collections import defaultdict
import copy
import enum
import itertools
from itertools import zip_longest
import math
import pprint
import string
import time

__version__ = "0.6"


punctuation = ".?!@#$%^&*:,<>{}[]\\|_-"
remove_punctuation = str.maketrans({x: " " for x in punctuation})

def _strip_leading_zeroes(s):
    if s.isdigit():
        return s.lstrip("0")
    return s

def str_to_keys(s):
    keys = s.lower().translate(remove_punctuation).strip().split()
    keys = [_strip_leading_zeroes(s) for s in keys]
    return keys


class FuzzyKey:
    """
    An abstract base class for "fuzzy" comparisons between keys.
    To use fuzzy matching, subclass FuzzyKey and implement
    both compare() and __hash__().
    """

    def compare(self, other):
        """
        FuzzyKey.compare() compares self against another
        value.  It should return a number in the range
        (0.0, 1.0).  (That is, 0.0 <= return_value <= 1.0.)
        The number returned indicates how good a match the
        two values are.
        1 indicates a perfect match.
        0 indicates the two values have nothing in common--
          a complete mismatch.

        If it's invalid to compare self against other,
        return NotImplemented.
        """
        return NotImplemented

    def __hash__(self):
        return id(self)


def item_key_score(item):
    return item.score

def sort_matches(matches):
    matches.sort(key=item_key_score)

def grouper(matches):
    """
    Splits matches into connected subgroups.

    In short:
      * if match1.value_a == match2.value_a,
        then they must be in the same "group" G.
        (Also true if they both have the same value_b.)
      * if match1.value_a != matchx.value_a for
        every matchx in group G, and similarly for value_b,
        then match1 must not be in group G.

    matches is an iterable of CorrelateMatch objects.
    grouper iterates over this list, storing them
    into a series of sub-lists where every match object
    has value_a or value_b in common with at least
    one other match object in that sub-list.

    Returns a list of these sub-lists, sorted by size,
    with the smallest sub-lists first.

    Sub-lists are guaranteed to be len() 1 or greater.
    """
    keys_a = {}
    keys_b = {}

    groups = []

    # i = lambda o: hex(id(o))[2:] #debug

    # print() #debug2
    # print("grouper input:") #debug2
    # pprint.pprint(matches) #debug2
    # print() #debug2

    for match in matches:
        # print("::", match) #debug2
        group_a = keys_a.get(match.value_a)
        group_b = keys_b.get(match.value_b)
        if group_a == group_b == None:
            l = []
            groups.append(l)
            # print(f"  new group {i(l)}") #debug2
        elif not (group_a and group_b) or (group_a == group_b):
            assert (group_a and not group_b) or (group_b and not group_a) or (group_a == group_b)
            l = group_a or group_b
            # print(f"     add to {i(l)}") #debug2
        else:
            # merge smaller into bigger
            if len(group_a) < len(group_b):
                smaller = group_a
                bigger = group_b
            else:
                bigger = group_a
                smaller = group_b
            # print("    merge smaller into bigger, add to bigger:") #debug2
            # print(f"         bigger {i(bigger)}") #debug2
            # print(f"        smaller {i(smaller)}") #debug2
            bigger.extend(smaller)
            for m in smaller:
                keys_a[m.value_a] = keys_b[m.value_b] = bigger
            l = bigger
            groups.remove(smaller)
        keys_a[match.value_a] = keys_b[match.value_b] = l
        l.append(match)

    groups.sort(key=len)
    # print() #debug2
    # print("grouper result:") #debug2
    # pprint.pprint(groups) #debug2
    # print() #debug2
    return groups


class MatchBoiler:
    """
    Boils down a list of CorrelatorMatch objects so that value_a and value_b attributes are unique,
    preserving what is hopefully the highest cumulative score.

    "matches" should be an iterable of objects with the following properties:
      * Every object in "matches" must have these attributes: "score", "value_a", and "value_b".
      * "score" must be a number.
      * "value_a" and "value_b" must support equality testing and must be hashable.
    The matches list is modified--if you don't want that, pass in a copy.
    The matches list you pass in MUST be sorted, with highest scores at the end.
      MatchBoiler is very careful to be stable, so it avoids re-sorting the list
      as it runs.  (Technically the list only has to be sorted at the time you call
      the object.)

    To actually compute the boiled-down list of matches, call the object.
    This returns a tuple of (results, seen_a, seen_b):
      * "results" is a filtered version of the "matches" list where any particular
        value of "value_a" or "value_b" appears only once (assuming reuse_a == reuse_b == False).
        "results" is sorted with highest score *first*.
      * seen_a is the set of values form value_a present in "results".
      * seen_b is the set of values from value_b present in "results".

    The match boiler attempts to maximize the sum of the "items" attributes.
    It uses a greedy algorithm: it sorts the incoming scores by score,
    and iteratively consumes the highest-scoring item, marking those "value_a" and "value_b"
    values as "used" as it goes.

    If it encounters multiple items with an identical score that have either
    "value_a" or "value_b" values in common, it (recursively) experimentally
    tries consuming each one and computes what the "results" would be.
    It then keeps the highest-scoring experiment.

    If reuse_a is True, the values of value_a in the returned "results"
    are permitted to repeat.  Similarly for reuse_b and value_b.
    """

    def __init__(self, *, matches = None, reuse_a=False, reuse_b=False,
        # name="match boiler", indent="", #debug
        ):
        self.reuse_a = reuse_a
        self.reuse_b = reuse_b
        self.seen_a = set()
        self.seen_b = set()
        if matches is None:
            matches = []
        self.matches = matches
        # self.name = name #debug
        # self.indent = indent #debug
        # self.print = print #debug

    def copy(self):
        copy = self.__class__(reuse_a=self.reuse_a, reuse_b=self.reuse_b)
        copy.seen_a = self.seen_a.copy()
        copy.seen_b = self.seen_b.copy()
        copy.matches = self.matches.copy()
        # copy.name = self.name #debug
        # copy.indent = self.indent #debug
        # copy.print = self.print #debug
        return copy

    def _assert_in_ascending_sorted_order(self):
        previous_score = -math.inf
        for i, item in enumerate(self.matches):
            assert previous_score <= item.score, f"{self.name}.matches not in ascending sorted order! {previous_score=} > matches[{i}].score {item.score}"
        return True

    def __call__(self):
        """
        invariants:
        * if "matches" is not empty, it contains CorrelatorMatch objects
          (or duck-typed equivalents), which are sorted by their "score"
          attributes, with lowest score first.
        * there must not be two items A and B in "matches"
          such that (A.value_a == B.value_b) and (A.value_b == B.value_b).
        """
        assert self._assert_in_ascending_sorted_order()

        matches = self.matches
        reuse_a = self.reuse_a
        reuse_b = self.reuse_b
        seen_a  = self.seen_a
        seen_b  = self.seen_b

        # sort_matches(matches)

        if (reuse_a and reuse_b):
            results = []
            while matches:
                item = matches.pop()
                results.append(item)
                seen_a.add(item.value_a)
                seen_b.add(item.value_b)
            return results, seen_a, seen_b

        results = []

        # self.print(f"{self.indent}{self.name} [{hex(id(self))[2:]}]: begin boiling!") #debug
        # self.print(f"{self.indent}    {len(self.matches)} items:") #debug
        # for item in self.matches: #debug
            # self.print(f"{self.indent}        {item}") #debug

        while matches:
            # consume the top-scoring item from matches.
            top_item = matches.pop()
            # self.print(f"{self.indent}    considering {top_item}") #debug
            # if we've already used value_a or value_b, discard
            if (
                ((not reuse_a) and (top_item.value_a in seen_a))
                or
                ((not reuse_b) and (top_item.value_b in seen_b))
                ):
                # self.print(f"{self.indent}        already used value_a or value_b, discarding.") #debug
                continue

            # the general case is: the top item's score is unique.
            # in that case, keep it, and loop immediately.
            top_score = top_item.score
            if (not matches) or (matches[-1].score != top_score):
                # self.print(f"{self.indent}        no other items with a matching score!  keep it!") #debug
                results.append(top_item)
                seen_a.add(top_item.value_a)
                seen_b.add(top_item.value_b)
                continue

            # okay, at least 2 of the top items in matches have the same score.
            # from here to the end of the loop is rarely-executed code,
            # so it doesn't need to be as performant. it's more important that
            # it be correct and readable.

            # consume all other items from matches that have the same score.
            matching_items = [top_item]
            while matches:
                if matches[-1].score != top_score:
                    break
                matching_item = matches.pop()
                if (
                    ((not reuse_a) and (matching_item.value_a in seen_a))
                    or
                    ((not reuse_b) and (matching_item.value_b in seen_b))
                    ):
                    continue
                matching_items.append(matching_item)

            # preserve order of matching items!
            matching_items = list(reversed(matching_items))

            groups = grouper(matching_items)

            # for disjoint items (items whose value_a and value_b
            # only appear once in matching_scores), immediately keep them.
            for group in groups:
                if len(group) == 1:
                    item = group[0]
                    results.append(item)
                    seen_a.add(item.value_a)
                    seen_b.add(item.value_b)
                    continue
                break
            else:
                continue

            # okay.  "group" now contains the smallest connected
            # list of matches with identical scores of length 2 or more.
            #
            # we need to recursively run experiments.
            # for each item in connected_items, try keeping it,
            # and computing what score we'd get from the rest
            # of the "scores" list.  then for each of these
            # experiments, compute the cumulative score.  then
            # keep the experiment with the greatest total score.
            #
            # this code preserves:
            #    * processing connected items in order
            #    * storing their results in order
            # the goal being: if the scores are all equivalent,
            # consume the first one.
            #
            # why is it best that this be the smallest group of
            # 2 or more?  because recursing on the smallest group
            # is cheapest.  let's say there are 50 items left
            # in matches.  and at the top are 5 items with the same
            # score.  one is a group of 2, the other is a group of 3.
            # the number of operations we'll perform by looping and
            # recursing is, roughly, NxM, where N is len(group)
            # and M is len(matches - group).  so which one is cheaper:
            #   2 x 48
            #   3 x 47
            # obviously the first one!

            assert len(group) >= 2
            # self.print(f"{self.indent}        recursing on smallest connected group, length {len(group)}.") #debug
            all_experiment_results = []

            for i in range(len(group) - 1, -1, -1):
                experiment = self.copy()
                # experiment.indent += "        " #debug
                matches = group.copy()
                item = matches.pop(i)
                experiment.matches.extend(matches)

                e_seen_a = experiment.seen_a
                e_seen_b = experiment.seen_b
                e_seen_a.add(item.value_a)
                e_seen_b.add(item.value_b)
                if not (reuse_a or reuse_b):
                    experiment.matches = [match for match in experiment.matches if ((match.value_a not in e_seen_a) and (match.value_b not in e_seen_b))]
                elif not reuse_a:
                    experiment.matches = [match for match in experiment.matches if match.value_a not in e_seen_a]
                elif not reuse_b:
                    experiment.matches = [match for match in experiment.matches if match.value_b not in e_seen_b]
                # self.print(f"{self.indent}        experiment #{len(group) - i}: keep {item}") #debug

                experiment_results, seen_a, seen_b = experiment()

                experiment_score = item.score + sum((o.score for o in experiment_results))
                all_experiment_results.append( (experiment_score, experiment, item, experiment_results, seen_a, seen_b) )

            #
            all_experiment_results.sort(key=lambda o: o[0], reverse=True)

            # these have already been filtered!
            experiment_score, experiment, item, experiment_results, seen_a, seen_b = all_experiment_results[0]
            results.append(item)
            results.extend(experiment_results)
            break

        # self.print(f"{self.indent}    returning {len(results)=}, {len(seen_a)=}, {len(seen_b)=}") #debug
        # self.print() #debug
        return results, seen_a, seen_b



class CorrelatorMatch:
    def __init__(self, value_a, value_b, score):
        self.value_a = value_a
        self.value_b = value_b
        self.score = score
        self.tuple = (self.score, self.value_a, self.value_b)

    def __repr__(self):
        return f"<CorrelatorMatch a={self.value_a!r} x b={self.value_b!r} = score={self.score}>"

    def __iter__(self):
        return iter(self.tuple)

class CorrelatorResult:
    def __init__(self, matches, unmatched_a, unmatched_b, minimum_score):
        self.matches = matches
        self.unmatched_a = unmatched_a
        self.unmatched_b = unmatched_b
        self.minimum_score = minimum_score

    def __repr__(self):
        return f"<CorrelatorResult {len(self.matches)} matches {len(self.unmatched_a)} unmatched_a {len(self.unmatched_b)} unmatched_b>"

    def normalize(self, *, high=None, low=None):
        """
        Adjusts scores so they fall in the range [0.0, 1.0).
        """
        if high is None:
            high = self.matches[0].score
        if low is None:
            low = self.minimum_score
        delta = high - low

        for match in self.matches:
            match.score = (match.score - low) / delta

class CorrelatorRankingApproach(enum.IntEnum):
    InvalidRanking = 0,
    BestRanking = 1,
    AbsoluteRanking = 2,
    RelativeRanking = 3,

BestRanking = CorrelatorRankingApproach.BestRanking
AbsoluteRanking = CorrelatorRankingApproach.AbsoluteRanking
RelativeRanking = CorrelatorRankingApproach.RelativeRanking


def defaultdict_list():
    return defaultdict(list)

def defaultdict_set():
    return defaultdict(set)

def defaultdict_zero():
    return defaultdict(int)

def defaultdict_none():
    return defaultdict(type(None))

class Correlator:

    class Dataset:
        def __init__(self, default_weight=1, *, id=None):

            self.id = id
            self.default_weight = default_weight

            # we store the data in the dataset in a compact
            # and easy-to-modify format.  when we actually
            # do the correlation, we cache the data in a much
            # more performance-optimized format.

            # self.values[index] = value
            self.values = []

            # self._index_to_key[index][type(key)][key][round] = weight
            #                   ^      ^          ^    ^
            #                   |      |          |    +- list
            #                   |      |          +- defaultdict
            #                   |      +- defaultdict
            #                   +- list
            #
            # both fuzzy and exact keys are stored here;
            # for exact keys, type(key) is None.
            self._index_to_key = []

            # self._key_to_index[key][round] = {index1, index2, ...}
            self._key_to_index = defaultdict_list()

            # self._value_to_index[value] = index
            # note that values aren't *required* to be hashable.
            # but if they are, they get stored here,
            # and looking stuff up in there saves a lot of time.
            self._value_to_index = {}

            self._rankings = []
            self._lowest_ranking = math.inf
            self._highest_ranking = -math.inf
            self._rankings_count = 0

            self._max_round = 0


        def __repr__(self):
            return f"<Dataset {self.id}>"

        def _value_index(self, value):
            try:
                return self._value_to_index[value]
            except (TypeError, KeyError):
                try:
                    return self.values.index(value)
                except ValueError:
                    index = len(self.values)
                    self.values.append(value)
                    self._index_to_key.append(defaultdict(defaultdict_list))
                    try:
                        self._value_to_index[value] = index
                    except TypeError:
                        pass
                    return index

        def set(self, key, value, weight=None):
            if weight is None:
                weight = self.default_weight

            key_type = type(key) if isinstance(key, FuzzyKey) else None
            index = self._value_index(value)

            # _values_to_keys[index] is guaranteed to exist by value_index,
            # and from there it's two default dicts and a list.
            weights = self._index_to_key[index][key_type][key]
            round = len(weights)
            weights.append(weight)
            weights.sort(reverse=True)

            index_rounds = self._key_to_index[key]
            # the number of rounds we've stored can never be more
            # than one less than the round we're adding now
            assert len(index_rounds) >= round, f"{len(index_rounds)=} should be >= {round=}"
            if len(index_rounds) == round:
                index_rounds.append(set())
            index_rounds[round].add(index)

            self._max_round = max(self._max_round, round + 1)


        def set_keys(self, keys, value, weight=None):
            # maybe optimize this later
            for key in keys:
                self.set(key, value, weight)

        def value(self, value, *, ranking=None):
            assert (ranking is None) or isinstance(ranking, (int, float)), f"illegal ranking value {ranking!r}"
            index = self._value_index(value)
            while len(self._rankings) <= index:
                self._rankings.append(None)
            self._rankings[index] = ranking
            self._lowest_ranking = min(self._lowest_ranking, ranking)
            self._highest_ranking = max(self._highest_ranking, ranking)
            self._rankings_count += 1

        def _ranking(self, index):
            if index >= len(self._rankings):
                return None
            return self._rankings[index]

        def __setitem__(self, key, value):
            self.set(key, value)

        def _precompute_streamlined_data(self, other):
            empty_tuple = ()

            # computes the cached data for the actual correlate
            all_exact_keys = set()

            all_fuzzy_keys = defaultdict_set()

            # exact_rounds[index][round] = (set(d), d)
            # d[key] = (weight, index_count)
            # if no keys, exact_rounds[index] = [] # empty list
            exact_rounds = []

            # fuzzy_types[index][type] = [(key, weight, round#), ...]
            # all rounds are merged together
            # if no keys, fuzzy_types[index][type] won't be set
            fuzzy_types = []

            # total_keys[index] = count
            # used for score_ratio_bonus
            total_keys = []

            for index, type_to_key in enumerate(self._index_to_key):
                exact_keys = type_to_key[None]
                total_key_counter = 0

                rounds = []

                if exact_keys:
                    all_exact_keys.update(exact_keys)
                    maximum_round = 0
                    for key, key_rounds in exact_keys.items():
                        round_count = len(key_rounds)
                        total_key_counter += round_count
                        while maximum_round < len(key_rounds):
                            maximum_round += 1
                            rounds.append({})
                        for round, (d, weight) in enumerate(zip(rounds, key_rounds)):
                            index_rounds = other._key_to_index.get(key, empty_tuple)
                            if len(index_rounds) > round:
                                key_count = len(index_rounds[round])
                            else:
                                key_count = 0
                            d[key] = weight, key_count
                    rounds = [(set(d), d) for d in rounds]

                exact_rounds.append(rounds)

                types = {}
                fuzzy_types.append(types)

                for t, k in type_to_key.items():
                    if t is None:
                        continue

                    assert k
                    all_fuzzy_keys[t].update(k)

                    keys = []
                    types[t] = keys

                    for key, weights in k.items():
                        assert weights
                        total_key_counter += len(weights)
                        for round, weight in enumerate(weights):
                            keys.append( (key, weight, round) )

                total_keys.append(total_key_counter)


            return (
                all_exact_keys,
                all_fuzzy_keys,
                exact_rounds,
                fuzzy_types,
                total_keys,
                )


    def __init__(self, default_weight=1):
        self.dataset_a = self.Dataset(id="a", default_weight=default_weight)
        self.dataset_b = self.Dataset(id="b", default_weight=default_weight)
        self.datasets = [
            self.dataset_a,
            self.dataset_b,
            ]
        self.print = print
        self._fuzzy_score_cache = defaultdict(defaultdict_none)
        # self._match_boiler_times = [] #debug
        # self._fuzzy_boiler_times = [] #debug

    def _validate(self):
        # self.print(f"validating {self}") #debug

        for dataset in self.datasets:
            # invariant: values and _index_to_key must be the same length
            len_values = len(dataset.values)
            assert len_values == len(dataset._index_to_key)

            # invariant: each value must appear in values only once
            for i, value in enumerate(dataset.values):
                try:
                    found = dataset.values[i+1:].index(value)
                    assert found == i, f"found two instances of value {value} in dataset {dataset._id}, {i} and {found+i+1}"
                except ValueError:
                    continue

            # invariant: if a key maps to a value multiple times,
            # the weights must be sorted highest value first.
            for key_types in dataset._index_to_key:
                for key_type, keys in key_types.items():
                    for key, rounds in keys.items():
                        sorted_rounds = list(rounds)
                        sorted_rounds.sort(reverse=True)
                        assert sorted_rounds == rounds

            unused_indices = set(range(len_values))
            self._key_to_index = defaultdict_list()
            for key, rounds in dataset._key_to_index.items():
                previous_round = None
                for round in rounds:
                    # invariant: each value that a key maps to must be a valid index
                    for index in round:
                        assert 0 <= index < len_values
                        unused_indices.discard(index)
                    # invariant: each subsequent round must be a strict subset of the previous round
                    #
                    if previous_round is not None:
                        # round and previous_round are sets, this is set.issubset()
                        assert round <= previous_round

            # invariant: at least one key maps to every value
            assert not unused_indices

        # self.print("    validated!") #debug
        # self.print() #debug

        return True

    def correlate(self,
            *,
            minimum_score=0,
            score_ratio_bonus=1,
            ranking=BestRanking,
            ranking_bonus=0,
            ranking_factor=0,
            reuse_a=False,
            reuse_b=False,
            ):
        # self.print(f"correlate(") #debug
        # self.print(f"    {self=}") #debug
        # self.print(f"    {minimum_score=}") #debug
        # self.print(f"    {score_ratio_bonus=}") #debug
        # self.print(f"    {ranking=}") #debug
        # self.print(f"    {ranking_bonus=}") #debug
        # self.print(f"    {ranking_factor=}") #debug
        # self.print(f"    {reuse_a=}") #debug
        # self.print(f"    {reuse_b=}") #debug
        # self.print(f"    )") #debug
        # self.print() #debug

        assert self._validate()

        a = self.dataset_a
        b = self.dataset_b
        fuzzy_score_cache = self._fuzzy_score_cache

        assert minimum_score >= 0

        empty_set = set()
        empty_dict = {}

        all_exact_keys_a, all_fuzzy_keys_a, exact_rounds_a, fuzzy_types_a, total_keys_a = a._precompute_streamlined_data(b)
        all_exact_keys_b, all_fuzzy_keys_b, exact_rounds_b, fuzzy_types_b, total_keys_b = b._precompute_streamlined_data(a)

        # dump datasets
        # for dataset, exact_rounds, fuzzy_types in ( #debug
            # (self.dataset_a, exact_rounds_a, fuzzy_types_a), #debug
            # (self.dataset_b, exact_rounds_b, fuzzy_types_b), #debug
            # ): #debug
            # self.print(f"[dataset {dataset.id}]") #debug
            # def print_key_and_weight(key, weight): #debug
                # if weight != dataset.default_weight: #debug
                    # weight_suffix = f" weight={weight}" #debug
                # else: #debug
                    # weight_suffix = "" #debug
                # self.print(f"                {key!r}{weight_suffix}") #debug

            # for index, (value, exact_round, fuzzy_round) in enumerate(zip(dataset.values, exact_rounds, fuzzy_types)): #debug
                # self.print(f"    value {index} {value!r}") #debug
                # if exact_round: #debug
                    # self.print(f"        exact keys") #debug
                # for round_number, (keys, weights) in enumerate(exact_round): #debug
                    # self.print(f"            round {round_number}") #debug
                    # keys = list(sorted(keys)) #debug
                    # for key in keys: #debug
                        # print_key_and_weight(key, weights[key][1]) #debug

                # for fuzzy_type, fuzzy_keys in fuzzy_round.items(): #debug
                    # self.print(f"        fuzzy type {fuzzy_type}") #debug

                    # for round_number in range(dataset._max_round): #debug
                        # self.print(f"            round {round_number}") #debug
                        # printed = False #debug
                        # for t in fuzzy_keys: #debug
                            # key, weight, round = t #debug
                            # if round == round_number: #debug
                                # printed = True #debug
                                # print_key_and_weight(key, weight) #debug
                        # if not printed: #debug
                            # break #debug
                        # round_number += 1 #debug

                # self.print() #debug


        # correlate makes four passes over the list of possible matches.

        # the first pass computes exact matches, and exact scores, and fuzzy matches.
        # however, we can't compute the final fuzzy scores in the first pass,
        # because we don't yet know the cumulative score for each fuzzy key.
        # those cumulative scores are stored in
        # that has to wait for the second pass.
        #
        # matches that have a fuzzy score are sent to the "second_pass".
        # matches that don't have a fuzzy score skip the "second_pass" and go straight into the "third_pass".

        # here we compute all_indexes, the list of indexes to compute as possible matches.
        # we compute this list as follows:
        #     store all indexes in all_indexes,
        #     then sort all_indexes,
        #     then strip out duplicates.
        #
        # sounds wasteful?  maybe!  but it's measurably faster
        # than my old approach, using a custom iterator:
        #
        #    seen = set()
        #    for indexes in all possible indexes:
        #        if indexes not in seen:
        #           yield indexes
        #           seen.add(indexes)
        #
        # this approach has the added feature of making the
        # algorithm more stable and predictable.
        # which means bugs should be stable and predictable, aka reproducable.

        all_indexes = []

        # only add indexes when they have exact keys in common.
        #
        # you only need to consider round 0, becuase again round N
        # is guaranteed to be a subset of round N-1.
        exact_keys = all_exact_keys_a & all_exact_keys_b
        for key in exact_keys:
            all_indexes.extend(itertools.product(a._key_to_index[key][0], b._key_to_index[key][0]))

        # add indexes for values that have fuzzy keys that,
        # when matched, have a fuzzy score > 0.
        # we compute and cache all fuzzy scores here.
        for fuzzy_type, fuzzy_keys_a in all_fuzzy_keys_a.items():
            fuzzy_keys_b = all_fuzzy_keys_b.get(fuzzy_type)
            if not fuzzy_keys_b:
                continue

            # technically we should check to see if we've cached the fuzzy score already.
            # however, it's rare that you actually reuse a fuzzy key.  so it's faster
            # in the long run to just make the redundant computations, rather than
            # carefully check for the cache first.
            for key_a, key_b in itertools.product(fuzzy_keys_a, fuzzy_keys_b):
                if key_a is key_b:
                    fuzzy_score = 1.0
                else:
                    fuzzy_score = key_a.compare(key_b)
                if fuzzy_score is NotImplemented:
                    fuzzy_score = key_b.compare(key_a)
                    if fuzzy_score is NotImplemented:
                        fuzzy_score = 0

                assert 0 <= fuzzy_score <= 1
                fuzzy_score_cache[key_a][key_b] = fuzzy_score
                if fuzzy_score > 0:
                    all_indexes.extend(itertools.product(a._key_to_index[key_a][0], b._key_to_index[key_b][0]))

        all_indexes.sort()

        # clever hack for removing unique elements from a sorted list
        # Python 3.6+ only
        # courtesy Raymond Hettinger
        all_indexes = list(dict.fromkeys(all_indexes))


        # computed during first_pass:
        #
        # fuzzy_key_cumulative_score_a[fuzzy_round_tuple_a]
        #    -> cumulative score for all fuzzy matches involving this fuzzy key in this round
        #
        # a "fuzzy_round_tuple" is
        #    (key, weight, round_number)
        #
        # this is what's stored in the precomputed data for matching fuzzy keys.
        # and, since we have it handy and it's immutable, it is itself used as
        # a key to represent a fuzzy key from a particular round.
        fuzzy_key_cumulative_score_a = defaultdict(int)
        fuzzy_key_cumulative_score_b = defaultdict(int)

        # "second_pass" stores results of the first pass that have fuzzy matches.
        # once the first pass is done, we now know the cumulative raw score for each
        # fuzzy key, so we can
        #
        # specifically, second_pass is a sequence of these:
        #    ( (index_a, index_b), exact_scores, cumulative_exact_score, fuzzy_semifinal_matches )
        # exact_scores is an unsorted list of the scores from all exact matches,
        #    with weights and cumulative_a * cumulative_b factored in.
        # cumulative_exact_score is the sum of the raw exact scores
        #    (without weights or cumulative_a * cumulative_b).
        #    it's used for computing score_ratio_bonus.
        #
        # fuzzy_semifinal_matches is an unsorted list of partially-computed fuzzy matches.
        # it's a series of tuples like this:
        #    (fuzzy_score, weighted_score, fuzzy_round_tuple_a, fuzzy_round_tuple_b)
        # fuzzy_score is the raw fuzzy score from this match.
        # weighted_score is fuzzy_score cubed with weights applied.
        #    it still needs to be divided by the product of the cumuative fuzzy scores of the two fuzzy keys;
        #    that's what this second pass is for.
        #
        # the output of the second pass is stored in third_pass.
        second_pass = []

        # third_pass computes score_ratio_bonus, ranking_factor, and ranking_bonus for each match.
        # at the end of the third pass, every score is finalized.
        #
        # sspecifically, third pass is a sequence of these:
        #    ( (index_a, index_b), score, cumulative_score)
        #
        # the output of the third pass is stored in fourth_pass.

        third_pass = []

        # fourth_pass is a list of Correlations objects, each representing
        # a possible "ranking approach".
        # if the user specified a specific approach, or isn't using rankings,
        # fourth_pass will only contain one object.
        # if the user is using rankings and didn't specify an approach,
        # fourth_pass will contain two Correlations objects,
        # one representing absolute ranking,
        # and the other representing relative ranking.
        #
        # the fourth pass is where we use the "match boiler" to boil down
        # all our matches obeying reuse_a and reuse_b.
        fourth_pass = []

        class Correlations:
            def __init__(self, name):
                self.name = name
                self.matches = []
                fourth_pass.append(self)

            def add(self, index_a, index_b, score):
                self.matches.append(CorrelatorMatch(index_a, index_b, score))

        absolute_correlations = relative_correlations = None

        if ranking_factor and ranking_bonus:
            raise RuntimeError("correlate: can't use ranking_factor and ranking_bonus together")
        using_rankings = (
            (ranking_factor or ranking_bonus)
            and (a._rankings_count > 1)
            and (b._rankings_count > 1)
            )
        if using_rankings:
            if ranking in (AbsoluteRanking, BestRanking):
                absolute_correlations = Correlations("absolute")
            if ranking in (RelativeRanking, BestRanking):
                relative_correlations = Correlations("relative")

            ranking_range_a = a._highest_ranking - a._lowest_ranking
            ranking_range_b = b._highest_ranking - b._lowest_ranking
            widest_ranking_range = max(ranking_range_a, ranking_range_b)
            one_minus_ranking_factor = 1.0 - ranking_factor
        else:
            correlations = Correlations("unified")


        # self.print("[first pass]") #debug
        # self.print(f"    examining {len(all_indexes)} matches") #debug
        # self.print() #debug
        # match_log = defaultdict_list() #debug
        # def match_print(indexes, *a, sep=" "): #debug
            # s = sep.join(str(x) for x in a) #debug
            # match_log[indexes].append(s) #debug

        # index_padding_length = math.floor(math.log10(max(len(dataset.values) for dataset in self.datasets))) #debug

        for indexes in all_indexes:
            index_a, index_b = indexes

            # cumulative_possible_exact_score is the total score of actual matched keys for these indexes
            # this is used in the computation of score_ratio_bonus.
            cumulative_possible_exact_score = 0

            # match_print(indexes, f"first pass {index_a} x {index_b} :") #debug
            # match_print(indexes, f"    value a: index {index_a:>{index_padding_length}} {self.dataset_a.values[index_a]}") #debug
            # match_print(indexes, f"    value b: index {index_b:>{index_padding_length}} {self.dataset_b.values[index_b]}") #debug

            exact_scores = []

            rounds_a = exact_rounds_a[index_a]
            rounds_b = exact_rounds_b[index_b]

            i = 0
            for round_a, round_b in zip(rounds_a, rounds_b):
                # match_print(indexes, f"    exact round {i+1}") #debug
                keys_a, weights_a = round_a
                keys_b, weights_b = round_b

                keys_intersection = keys_a & keys_b
                if not keys_intersection:
                    # match_print(indexes, "        no intersecting keys, early-exit.") #debug
                    break

                try:
                    # why bother? this removes the last little bit of randomness from the algorithm.
                    keys_intersection = tuple(sorted(keys_intersection))
                except TypeError:
                    pass

                cumulative_possible_exact_score += len(keys_intersection) * 2

                # sorted_a = "{" + ", ".join(list(sorted(keys_a))) + "}" #debug
                # sorted_b = "{" + ", ".join(list(sorted(keys_b))) + "}" #debug
                # sorted_intersection = "{" + ", ".join(list(sorted(keys_intersection))) + "}" #debug
                # match_print(indexes, f"        keys in a {sorted_a}") #debug
                # match_print(indexes, f"        keys in b {sorted_b}") #debug
                # match_print(indexes, f"        keys in common {sorted_intersection}") #debug

                # weights = [dataset._rounds[0].map[key] for dataset in self.datasets]

                scored = False
                for key in keys_intersection:
                    weight_a, len_weights_a = weights_a[key]
                    weight_b, len_weights_b = weights_b[key]
                    score = (weight_a * weight_b) / (len_weights_a * len_weights_b)
                    # match_print(indexes, f"        score for matched key {key!r} =  {score} ({weight_a=} * {weight_b=}) / ({len_weights_a=} * {len_weights_b=})") #debug
                    if score:
                        scored = True
                        exact_scores.append(score)

                if not scored:
                    # match_print(indexes, "        no scores, early-exit.") #debug
                    break

                i += 1


            exact_score = sum(sorted(exact_scores))
            # match_print(indexes) #debug
            # match_print(indexes, f"    {exact_scores=}, {exact_score=}") #debug

            # we're only interested in types that are in both a and b
            # therefore we can iterate over a and check for it in b

            fuzzy_a = fuzzy_types_a[index_a]
            fuzzy_b = fuzzy_types_b[index_b]
            # TODO
            #
            # this is a possible source of randomness in the algorithm.
            #
            # to fix: every time they set() a mapping,
            # if it's for a fuzzy type we haven't seen before,
            # assign that fuzzy type a monotonically increasing serial number.
            # then sort by those.
            fuzzy_types_in_common = fuzzy_a.keys() & fuzzy_b.keys()

            fuzzy_semifinal_matches = []

            for fuzzy_type in fuzzy_types_in_common:

                # start = time.perf_counter() #debug

                fuzzy_boiler = MatchBoiler()
                # fuzzy_boiler.name = "fuzzy boiler" #debug
                # fuzzy_boiler.print = self.print #debug

                for pair in itertools.product(fuzzy_a[fuzzy_type], fuzzy_b[fuzzy_type]):
                    tuple_a, tuple_b = pair
                    key_a, weight_a, round_a = tuple_a
                    key_b, weight_b, round_b = tuple_b
                    fuzzy_score = fuzzy_score_cache[key_a][key_b]
                    # match_print(indexes, f"                {key_a=} x {key_b=} = {fuzzy_score=}") #debug

                    if fuzzy_score <= 0:
                        continue

                    fuzzy_score_cubed = fuzzy_score ** 3

                    weighted_score = (weight_a * weight_b) * fuzzy_score_cubed

                    lowest_round = min(round_a, round_b)
                    highest_round = max(round_a, round_b)
                    sort_by = (fuzzy_score, -lowest_round, -highest_round)

                    # match_print(indexes, f"                    weights=({weight_a}, {weight_b}) {weighted_score=}") #debug
                    item = CorrelatorMatch(tuple_a, tuple_b, fuzzy_score)
                    item.scores = (fuzzy_score, weighted_score)
                    item.sort_by = sort_by
                    fuzzy_boiler.matches.append(item)
                fuzzy_boiler.matches.sort(key=lambda x : x.sort_by)

                fuzzy_matches = fuzzy_boiler()[0]

                # end = time.perf_counter() #debug
                # self._fuzzy_boiler_times.append(end - start) #debug

                for item in fuzzy_matches:
                    fuzzy_score, tuple_a, tuple_b = item
                    fuzzy_key_cumulative_score_a[tuple_a] += fuzzy_score
                    fuzzy_key_cumulative_score_b[tuple_b] += fuzzy_score
                    fuzzy_score, weighted_score = item.scores
                    fuzzy_semifinal_matches.append( (fuzzy_score, weighted_score, tuple_a, tuple_b) )

            if not fuzzy_semifinal_matches:
                # match_print(indexes, f"    no fuzzy scores.  add to third pass.") #debug
                # match_print(indexes, "") #debug
                third_pass.append( (indexes, exact_score, cumulative_possible_exact_score) )
                continue

            # goes into second_pass to await final computation
            plural = "" if len(fuzzy_semifinal_matches) == 1 else "s"
            # match_print(indexes) #debug
            # match_print(indexes, f"    {len(fuzzy_semifinal_matches)} fuzzy score{plural} added to second pass.") #debug
            # match_print(indexes) #debug
            second_pass.append( ( indexes, exact_scores, cumulative_possible_exact_score, fuzzy_semifinal_matches ) )

        # if not second_pass: #debug
            # self.print("[skipping second pass (no fuzzy keys!)]") #debug
            # self.print("") #debug
        # else: #debug
            # self.print("[second pass]") #debug
            # self.print(f"    {len(second_pass)} matches with fuzzy components to fix up.") #debug
            # self.print() #debug

        for t in second_pass:
            indexes, exact_scores, cumulative_score, fuzzy_semifinal_matches = t
            # index_a, index_b = indexes #debug
            # match_print(indexes, f"second pass {index_a} x {index_b} :") #debug
            # match_print(indexes, f"    {exact_scores=}") #debug
            # match_print(indexes) #debug

            for t2 in fuzzy_semifinal_matches:
                fuzzy_score, weighted_score, tuple_a, tuple_b = t2
                # key_a = tuple_a[0] #debug
                # key_b = tuple_b[0] #debug
                # match_print(indexes, f"    {key_a=}") #debug
                # match_print(indexes, f"    {key_b=}") #debug
                hits_in_a = fuzzy_key_cumulative_score_a[tuple_a]
                hits_in_b = fuzzy_key_cumulative_score_b[tuple_b]
                score = weighted_score / (hits_in_a * hits_in_b)
                cumulative_score += fuzzy_score * 2
                # match_print(indexes, f"    {score=} = {weighted_score=} / ({hits_in_a=} * {hits_in_b=})") #debug
                # match_print(indexes) #debug
                exact_scores.append(score)
            exact_scores.sort()
            score = sum(exact_scores)
            # match_print(indexes, f"    final {score=}") #debug
            # match_print(indexes) #debug
            third_pass.append( (indexes, score, cumulative_score) )

        # self.print("[third pass]") #debug
        # self.print() #debug
        for t in third_pass:
            indexes, score, cumulative_actual_score = t
            index_a, index_b = indexes
            # match_print(indexes, f"third pass {index_a} x {index_b} :") #debug
            # match_print(indexes, f"    score = {score}") #debug

            if score_ratio_bonus:
                bonus = (
                    (score_ratio_bonus * cumulative_actual_score)
                    / (total_keys_a[index_a] + total_keys_b[index_b])
                    )
                # match_print(indexes, f"    hit ratio {bonus=} = {score_ratio_bonus=} * {cumulative_actual_score=}) / ({total_keys_a[index_a]=} + {total_keys_b[index_b]=})") #debug
                score += bonus

            if not using_rankings:
                # match_print(indexes, f"    {score=}") #debug
                # match_print(indexes) #debug
                correlations.add(index_a, index_b, score)
                continue

            # match_print(indexes, f"    pre-ranking {score=}") #debug
            absolute_score = relative_score = score
            ranking_a = self.dataset_a._ranking(index_a)
            ranking_b = self.dataset_b._ranking(index_b)

            if (ranking_a is not None) and (ranking_b is not None):
                relative_a = ranking_a / ranking_range_a
                relative_b = ranking_b / ranking_range_b
                relative_distance_factor = 1 - abs(relative_a - relative_b)

                absolute_distance_factor = 1 - (abs(ranking_a - ranking_b) / widest_ranking_range)

                if ranking_factor:
                    # match_print(indexes, ) #debug
                    # match_print(indexes, f"    ranking factors:") #debug
                    # match_print(indexes, f"        {absolute_distance_factor=}") #debug
                    # match_print(indexes, f"        {relative_distance_factor=}") #debug
                    absolute_score *= one_minus_ranking_factor + (ranking_factor * absolute_distance_factor)
                    relative_score *= one_minus_ranking_factor + (ranking_factor * relative_distance_factor)
                elif ranking_bonus:
                    absolute_score += ranking_bonus * absolute_distance_factor
                    relative_score += ranking_bonus * relative_distance_factor
                    # match_print(indexes, f"    rank-based scores:") #debug
                    # match_print(indexes, f"        {absolute_score=}") #debug
                    # match_print(indexes, f"        {relative_score=}") #debug
            else:
                # if we don't have valid ranking for both sides,
                # and ranking_factor is in use,
                # we need to penalize this match so matches with ranking info are worth more
                if ranking_factor:
                    absolute_score *= one_minus_ranking_factor
                    relative_score *= one_minus_ranking_factor

            # match_print(indexes, f"    final rank-based scores:") #debug
            # match_print(indexes, f"        {absolute_score=}") #debug
            # match_print(indexes, f"        {relative_score=}") #debug
            # match_print(indexes) #debug

            if absolute_correlations is not None:
                absolute_correlations.add(index_a, index_b, absolute_score)
            if relative_correlations is not None:
                relative_correlations.add(index_a, index_b, relative_score)

        # for indices in all_indexes: #debug
            # l = match_log[indices] #debug
            # s = "\n".join(l) #debug
            # self.print(s) #debug

        # self.print("[fourth pass (choose ranking)]") #debug
        results = []

        # fourth pass!
        for correlations in fourth_pass:
            matches = correlations.matches
            sort_matches(matches)
            # throw away matches with score < minimum_score
            for i, item in enumerate(matches):
                if item.score > minimum_score:
                    matches = matches[i:]
                    break
            else:
                matches = []

            # start = time.perf_counter() #debug
            boiler = MatchBoiler(matches=matches, reuse_a=reuse_a, reuse_b=reuse_b)
            # boiler.print = self.print #debug
            matches, seen_a, seen_b = boiler()
            # end = time.perf_counter() #debug
            # self._match_boiler_times.append(end - start) #debug

            cumulative_score = sum(item.score for item in matches)

            if matches:
                # clipped_score_integer, dot, clipped_score_fraction = str(cumulative_score).partition(".") #debug
                # clipped_score = f"{clipped_score_integer}{dot}{clipped_score_fraction[:4]}" #debug
                # self.print(f"    {correlations.name}:") #debug
                # self.print(f"        cumulative_score {clipped_score}, {len(matches)} matches, {len(seen_a)} seen_a, {len(seen_b)} seen_b") #debug
                results.append((cumulative_score, matches, seen_a, seen_b, correlations))

        if not results:
            matches = []
            unmatched_a = list(self.dataset_a.values)
            unmatched_b = list(self.dataset_b.values)
            # self.print(f"    no valid results!  returning 0 matches.  what a goof!") #debug
        else:
            results.sort(key=lambda x: x[0])
            # use the highest-scoring correlation
            cumulative_score, matches, seen_a, seen_b, correlations = results[-1]
            # self.print(f"    highest scoring result: {correlations.name!r} = {cumulative_score}") #debug
            unmatched_a = [value for i, value in enumerate(a.values) if i not in seen_a]
            unmatched_b = [value for i, value in enumerate(b.values) if i not in seen_b]
        # self.print() #debug

        for match in matches:
            match.value_a = a.values[match.value_a]
            match.value_b = b.values[match.value_b]

        # for name, l in ( #debug
                # ("match boiler", self._match_boiler_times), #debug
                # ("fuzzy boiler", self._fuzzy_boiler_times), #debug
            # ): #debug
            # l.sort() #debug
            # total = sum(l) #debug
            # print(f">> {name} cumulative time: {total}") #debug

        return CorrelatorResult(matches, unmatched_a, unmatched_b, minimum_score)
