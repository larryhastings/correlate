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
Correlates two sets of data by matching
unique or fuzzy keys between the two datasets.
"""

# TODO:
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
#             some sort of binary partitioning.  a la BSPs?

from collections import defaultdict
import enum
import itertools
import math
# import pprint #debug
import time

__version__ = "0.8.3"


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
      * if match1.value_a != match2.value_a for
        every match2 in group G, and similarly for value_b,
        then match1 *must not* be in group G.

    matches is an iterable of CorrelateMatch objects.
    grouper iterates over this list, storing them
    into a series of sub-lists where every match object
    has value_a or value_b in common with at least
    one other match object in that sub-list.  matches
    is not modified.

    Returns a list of these sub-lists, sorted by size,
    with the largest sub-lists first.

    Sub-lists are guaranteed to be len() 1 or greater.

    Sub-lists internally preserve the order of the matches
    passed in.  For every item1 and item2 in a sub-list,
    if item1 was before item2 in matches, item1 is guaranteed
    to be before item2 in that sub-list.

    Doesn't support reuse_a or reuse_b; use
    grouper_reuse_a() or grouper_reuse_b() for that.
    (If reuse_a == reuse_b == True, you don't need
    grouper() at all, you just keep everything.)
    """
    keys_a = {}
    keys_b = {}

    groups = []

    # i = lambda o: hex(id(o))[2:] #debug2

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
        elif (group_a == group_b) or not (group_a and group_b):
            assert (group_a and not group_b) or (group_b and not group_a) or (group_a == group_b)
            l = group_a or group_b
            # print(f"     add to {i(l)}") #debug2
        else:
            # merge smaller into bigger
            # that's cheaper, because we need to walk the group we discard
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

    groups.sort(key=len, reverse=True)
    # print() #debug2
    # print("grouper result:") #debug2
    # pprint.pprint(groups) #debug2
    # print() #debug2
    return groups


def grouper_reuse_a(matches):
    """
    Like grouper(), but with reuse_a == True.
    """

    # i = lambda o: hex(id(o))[2:] #debug

    # print() #debug2
    # print("grouper input:") #debug2
    # pprint.pprint(matches) #debug2
    # print() #debug2
    groups = defaultdict_list()

    for match in matches:
        # print("::", match) #debug2
        groups[match.value_b].append(match)
    groups = list(groups.values())
    groups.sort(key=len, reverse=True)
    return groups


def grouper_reuse_b(matches):
    """
    Like grouper(), but with reuse_b == True.
    """

    # i = lambda o: hex(id(o))[2:] #debug

    # print() #debug2
    # print("grouper input:") #debug2
    # pprint.pprint(matches) #debug2
    # print() #debug2
    groups = defaultdict_list()

    for match in matches:
        # print("::", match) #debug2
        groups[match.value_a].append(match)
    groups = list(groups.values())
    groups.sort(key=len, reverse=True)
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
      (Technically the list only has to be sorted at the time you call the object,
      not when it's passed in to the constructor.)

    To actually compute the boiled-down list of matches, call the object.
    This returns a tuple of (results, seen_a, seen_b):
      * "results" is a filtered version of the "matches" list where any particular
        value of "value_a" or "value_b" appears only once (assuming reuse_a == reuse_b == False).
        "results" is sorted with highest score *first*.  Note, this is the opposite of the input
        list "matches".  Apart from reversing and filtering the values, MatchBoiler is stable;
        the entries in "results" are guaranteed to be in the same (reversed) order they were
        in "matches".
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

    (You *can* call the boiler with reuse_a == reuse_b == True.
     But in that case you didn't really need a boiler, now did you!)
    """

    def __init__(self, matches = None, *, reuse_a=False, reuse_b=False,
        # name="match boiler", indent="", #debug
        ):
        if matches is None:
            matches = []
        self.matches = matches
        self.reuse_a = reuse_a
        self.reuse_b = reuse_b

        # self.name = name #debug
        # self.indent = indent #debug
        self.print = print

        self.seen_a = set()
        self.seen_b = set()
        if reuse_a:
            self.grouper = grouper_reuse_a
        elif reuse_b:
            self.grouper = grouper_reuse_b
        else:
            self.grouper = grouper

    def copy(self):
        copy = self.__class__(reuse_a=self.reuse_a, reuse_b=self.reuse_b)
        copy.seen_a = self.seen_a.copy()
        copy.seen_b = self.seen_b.copy()
        copy.matches = self.matches.copy()
        copy.print = self.print
        copy.grouper = self.grouper
        # copy.name = self.name #debug
        # copy.indent = self.indent #debug
        return copy

    def _assert_in_ascending_sorted_order(self):
        previous_score = -math.inf
        for i, item in enumerate(self.matches):
            assert previous_score <= item.score, f"{self.name}.matches not in ascending sorted order! previous_score {previous_score} > matches[{i}].score {item.score}"
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
        grouper = self.grouper

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

        # self.print(f"{self.indent}{self.name} [{hex(id(self))}]: begin boiling!") #debug
        # self.print(f"{self.indent}    {len(self.matches)} items") #debug
        # only print all the matches if it's not hyooge
        # if len(self.matches) < 50: #debug
            # for item in self.matches: #debug
                # self.print(f"{self.indent}        {item}") #debug
            # self.print() #debug

        while matches:
            # consume the top-scoring item from matches.
            top_item = matches.pop()
            # if we've already used value_a or value_b, discard
            if (
                ((not reuse_a) and (top_item.value_a in seen_a))
                or
                ((not reuse_b) and (top_item.value_b in seen_b))
                ):
                # text = [] #debug
                # if (not reuse_a) and (top_item.value_a in seen_a): #debug
                    # text.append("value_a") #debug
                # if (not reuse_b) and (top_item.value_b in seen_b): #debug
                    # text.append("value_b") #debug
                # text = " *and* ".join(text) #debug
                # self.print(f"{self.indent}    {top_item}: discarding, already seen {text}.") #debug
                continue

            # the general case is: the top item's score is unique.
            # in that case, keep it, and loop immediately.
            top_score = top_item.score
            if (not matches) or (matches[-1].score != top_score):
                # self.print(f"{self.indent}    {top_item}: it's a match!") #debug
                results.append(top_item)
                seen_a.add(top_item.value_a)
                seen_b.add(top_item.value_b)
                continue

            # self.print(f"{self.indent}    {top_item}: may need to recurse!") #debug

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
                    # text = [] #debug
                    # if (not reuse_a) and (matching_item.value_a in seen_a): #debug
                        # text.append("value_a") #debug
                    # if (not reuse_b) and (matching_item.value_b in seen_b): #debug
                        # text.append("value_b") #debug
                    # text = " *and* ".join(text) #debug
                    # self.print(f"{self.indent}    {matching_item}: score matches, but discarding, already seen {text}.") #debug
                    continue
                matching_items.append(matching_item)

            if len(matching_items) == 1:
                # self.print(f"{self.indent}        we only had one usable match in this run of matching scores.  keep it and move on.") #debug
                results.append(top_item)
                seen_a.add(top_item.value_a)
                seen_b.add(top_item.value_b)
                continue

            # we're going to preserve order for the output items.
            # this is a little tricky!

            # first, we need a place to put all the items from
            # matching_items that we've kept.  the order of items
            # in here is gonna get scrambled; we'll restore it at the end.
            kept_items = []

            # grouper is guaranteed non-destructive.
            groups = grouper(matching_items)

            # for disjoint items (items whose value_a and value_b
            # only appear once in matching_scores), immediately keep them.
            # if we only ever found groups of length 1, the for/else means
            # we'll continue the outer loop and continue iterating through matches.
            # if we find a group of length 2 or greater we break.
            while groups:
                group = groups.pop()
                if len(group) == 1:
                    item = group[0]
                    # self.print(f"{self.indent}    {item}: unconnected, keeping match.") #debug
                    kept_items.append(item)
                    seen_a.add(item.value_a)
                    seen_b.add(item.value_b)
                    continue
                break
            else:
                # self.print(f"{self.indent}        no connected groups! no need to recurse. continuing.") #debug
                # flush kept items
                assert len(kept_items) > 1
                ordering_map = {item: i for i, item in enumerate(matching_items)}
                kept_items.sort(key=ordering_map.get)
                results.extend(kept_items)
                continue

            # okay.  "group" now contains the smallest connected
            # list of matches with identical scores of length 2 or more.
            # and "groups" contains all other groups of size 2 or more.
            #
            # we need to recursively run experiments.
            # for each item in the group, try keeping it,
            # recursively process the rest of the matches,
            # and compute the resulting cumulative score.
            # then keep the experiment with the greatest cumulative score.
            #
            # this code preserves:
            #    * processing connected items in order
            #    * storing their results in order
            # the goal being: if the scores are all equivalent,
            # keep the first one.
            #
            # why is it best that this be the smallest group of
            # 2 or more?  because recursing on the smallest group
            # is cheapest.  let's say there are 50 items left
            # in matches.  at the top are 6 items with the same
            # score.  one is a group of 2, the other is a group of 4.
            # the number of operations we'll perform by looping and
            # recursing is, roughly, NxM, where N is len(group)
            # and M is len(matches - group).  so which one is cheaper:
            #   2 x 48
            #   4 x 46
            # obviously the first one!

            assert len(group) >= 2

            # self.print(f"{self.indent}        recursing on smallest connected group, length {len(group)}.") #debug
            merged_groups = list(group)
            for group in groups:
                merged_groups.extend(group)
            # reorder merged_groups so it's in original (not reversed) order.
            # again, we're striving for *absolute* stability here.
            # we want to do the recursions in original order, then sort
            # by overall score.  that way, if there are multiple results
            # with the same highest overall score, and we use the *first*
            # one, we're guaranteed that it's the earliest one from the
            # original matches.
            if len(merged_groups) > 1:
                ordering_map = {item: i for i, item in enumerate(reversed(matching_items))}
                merged_groups.sort(key=ordering_map.get)

            all_experiment_results = []

            assert len(group) > 1
            assert len(merged_groups) > 1

            for i in range(len(group) - 1, -1, -1):
                matches = merged_groups.copy()
                item = matches.pop(i)

                experiment = self.copy()
                # experiment.indent += "        " #debug
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

                if len(experiment.matches) >= 2:
                    experiment_results, seen_a, seen_b = experiment()

                    experiment_score = item.score + sum((o.score for o in experiment_results))
                else:
                    if not experiment.matches:
                        experiment_results = ()
                        experiment_score = 0
                        # s = "no items" #debug
                    else:
                        experiment_results = experiment.matches
                        experiment_score = experiment.matches[0].score
                        # s = "only 1 item" #debug
                    # self.print(f"{self.indent}            don't bother recursing! {s}.  score: {experiment_score}") #debug
                    seen_a = e_seen_a
                    seen_b = e_seen_b

                all_experiment_results.append( (experiment_score, item, experiment_results, seen_a, seen_b) )

            assert len(all_experiment_results) > 1
            all_experiment_results.sort(key=lambda o: o[0], reverse=True)
            experiment_score, item, experiment_results, seen_a, seen_b = all_experiment_results[0]

            # here's where we restore the order of kept_items.
            # first, move *all* the items we kept from this run
            # of identically-scored items into kept_items.
            # that means the item we recursed on:
            kept_items.append(item)

            # and all the items in experiment_results with the same score.
            # naturally, experiment_results is already sorted, with highest score first,
            # and there are guaranteed to be no items with a score > top_score.
            # we need to move these into kept_items because we need to mix them
            # back in with the items from the connected groups of length 1, and
            # sort them all together into happy smiling original (reversed!) sorted order.
            for i, item in enumerate(experiment_results):
                if item.score != top_score:
                    break
            else:
                i = len(experiment_results)

            if i:
                kept_items.extend(experiment_results[:i])
                experiment_results = experiment_results[i:]
            assert all([item.score == top_score for item in kept_items])
            assert all([item.score != top_score for item in experiment_results])

            # now the clever part: sort kept_items back into the original order!
            if len(kept_items) > 1:
                ordering_map = {item: i for i, item in enumerate(matching_items)}
                kept_items.sort(key=ordering_map.get)

            results.extend(kept_items)
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

    def __hash__(self):
        return hash(self.tuple)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.tuple == other.tuple
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if not isinstance(other, self.__class__):
            raise ValueError("can only compare to other members of " + self.__class__.__name__)
        return self.tuple < other.tuple



class CorrelatorResult:
    def __init__(self, matches, unmatched_a, unmatched_b, minimum_score, statistics):
        self.matches = matches
        self.unmatched_a = unmatched_a
        self.unmatched_b = unmatched_b
        self.minimum_score = minimum_score
        self.statistics = statistics

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
    RankingNotUsed = 0,
    BestRanking = 1,
    AbsoluteRanking = 2,
    RelativeRanking = 3,

RankingNotUsed = CorrelatorRankingApproach.RankingNotUsed
BestRanking = CorrelatorRankingApproach.BestRanking
AbsoluteRanking = CorrelatorRankingApproach.AbsoluteRanking
RelativeRanking = CorrelatorRankingApproach.RelativeRanking


def defaultdict_list():
    return defaultdict(list)

def defaultdict_set():
    return defaultdict(set)

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
            assert len(index_rounds) >= round, f"len(index_rounds)={len(index_rounds)}, should be >= round {round}"
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

            # fuzzy_types[index][type] = [
            #                              [(key1, weight, round#0),  (key1, weight, round#1), ...],
            #                              [(key2, weight, round#0),  (key2, weight, round#1), ...],
            #                            ]
            #
            # if there are no keys, fuzzy_types[index][type] won't be set
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
                            index_rounds = self._key_to_index.get(key, empty_tuple)
                            if len(index_rounds) > round:
                                key_count = len(index_rounds[round])
                                score = weight / key_count
                            else:
                                score = 0.0

                            # I used to store d[key] = (weight, key_count)
                            # then compute the exact key score with
                            #    weight_a, key_count_a = weights_a[key]
                            #    weight_b, key_count_b = weights_b[key]
                            #    score = (weight_a * weight_b) / (key_count_a / key_count_b)
                            # But pre-dividing the score by the key count speeds up the
                            # overall algorithm by maybe 1%.  And it works fine
                            # because the calculation is symmetric.
                            #
                            # Doing it this way *does* introduce a little error.
                            # Very, very little.  The average error is < 1.5e-17.
                            # Uh, yeah, I can live with that for a 1% speedup.
                            d[key] = score
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
                        subkeys = []
                        for round, weight in enumerate(weights):
                            subkeys.append( (key, weight, round) )
                        keys.append(subkeys)

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

    def print_datasets(self):
        all_exact_keys_a, all_fuzzy_keys_a, exact_rounds_a, fuzzy_types_a, total_keys_a = self.dataset_a._precompute_streamlined_data(self.dataset_b)
        all_exact_keys_b, all_fuzzy_keys_b, exact_rounds_b, fuzzy_types_b, total_keys_b = self.dataset_b._precompute_streamlined_data(self.dataset_a)

        for dataset, exact_rounds, fuzzy_types in (
            (self.dataset_a, exact_rounds_a, fuzzy_types_a),
            (self.dataset_b, exact_rounds_b, fuzzy_types_b),
            ):
            self.print(f"[dataset {dataset.id}]")
            def print_key_and_weight(key, weight):
                if weight != dataset.default_weight:
                    weight_suffix = f" weight={weight}"
                else:
                    weight_suffix = ""
                self.print(f"                {key!r}{weight_suffix}")

            for index, (value, exact_round, fuzzy_round) in enumerate(zip(dataset.values, exact_rounds, fuzzy_types)):
                self.print(f"    value {index} {value!r}")
                if exact_round:
                    self.print(f"        exact keys")
                for round_number, (keys, weights) in enumerate(exact_round):
                    self.print(f"            round {round_number}")
                    type_to_keys = defaultdict(list)
                    for key in keys:
                        type_to_keys[type(key)].append(key)
                    keys = []
                    key_types = sorted(type_to_keys.keys(), key=lambda t: str(t))
                    for key_type in key_types:
                        keys.extend(sorted(type_to_keys[key_type]))
                    for key in keys:
                        # weights in exact_round are pre-divided by key count!
                        # let's print the unmodified weight.
                        weight = dataset._index_to_key[index][None][key][round_number]
                        print_key_and_weight(key, weight)

                for fuzzy_type, fuzzy_key_lists in fuzzy_round.items():
                    self.print(f"        fuzzy type {fuzzy_type}")

                    for fuzzy_keys in fuzzy_key_lists:
                        for round_number in range(dataset._max_round):
                            self.print(f"            round {round_number}")
                            printed = False
                            for t in fuzzy_keys:
                                key, weight, round = t
                                if round == round_number:
                                    printed = True
                                    print_key_and_weight(key, weight)
                            if not printed:
                                break
                            round_number += 1

                self.print()

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
            if unused_indices:
                raise ValueError(f"dataset {dataset.id}: {len(unused_indices)} values with no keys! " + " ".join(f"#{unused}={dataset.values[unused]}" for unused in unused_indices))

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
        correlate_start = time.perf_counter()

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
        # self.print_datasets() #debug

        assert self._validate()

        a = self.dataset_a
        b = self.dataset_b
        fuzzy_score_cache = self._fuzzy_score_cache

        assert minimum_score >= 0

        statistics = {
            "minimum_score"     : minimum_score,
            "score_ratio_bonus" : score_ratio_bonus,
            "ranking"           : ranking,
            "ranking_bonus"     : ranking_bonus,
            "ranking_factor"    : ranking_factor,
            "reuse_a"           : reuse_a,
            "reuse_b"           : reuse_b,
        }

        empty_dict = {}
        empty_set = set()
        empty_tuple = ()

        # correlate makes six passes over all the data.
        #
        # pass 1: compute the streamlined data for the two datasets.
        # pass 2: compute the list of indices (pairs of indexes)
        #         for all matches with a nonzero score.
        #         note that this pass also performs all fuzzy key comparisons,
        #         and caches their results.
        # pass 3: for every indices pair,
        #           compute a subtotal score for every fuzzy key match.
        # pass 4: for every indices pair,
        #           compute the score for all exact keys,
        #           finalize the fuzzy key match scores,
        #           compute the bonuses (score_ratio_bonus, ranking),
        #           and store in the appropriate list of matches.
        # pass 5: for every ranking approach being used,
        #           compute the final list of successful matches
        #           (using the "match boiler" and "greedy algorithm").
        # pass 6: choose the ranking approach with the highest cumulative score,
        #           compute unseen_a and unseen_b,
        #           and back-substitute the "indexes" with their actual values
        #           before returning.


        #
        # pass 1
        #
        # self.print("[pass 1: precompute streamlined data]") #debug
        pass_start = time.perf_counter()
        all_exact_keys_a, all_fuzzy_keys_a, exact_rounds_a, fuzzy_types_a, total_keys_a = a._precompute_streamlined_data(b)
        all_exact_keys_b, all_fuzzy_keys_b, exact_rounds_b, fuzzy_types_b, total_keys_b = b._precompute_streamlined_data(a)

        end = time.perf_counter()
        statistics['pass 1 time'] = end - pass_start
        # self.print(f"[pass 1 time: {statistics['pass 1 time']}]") #debug
        # self.print() #debug


        # pass 2
        #
        # self.print("[pass 2: compute index pairs for all matches]") #debug

        # here we compute all_indexes, the list of indexes to compute as possible matches.
        # we compute this list as follows:
        #     store all indexes in all_indexes,
        #     then convert to a list and sort.
        #
        # it's measurably faster than my old approach, which used a custom iterator:
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
        #

        pass_start = start = end
        all_indexes = set()

        # only add indexes when they have exact keys in common.
        #
        # we only need to consider round 0,
        # because the set of keys in round N
        # is *guaranteed* to be a subset of the keys in round N-1.
        # therefore round 0 always contains all keys.
        exact_keys = all_exact_keys_a & all_exact_keys_b
        for key in exact_keys:
            all_indexes.update(itertools.product(a._key_to_index[key][0], b._key_to_index[key][0]))

        end = time.perf_counter()
        statistics['pass 2 exact indexes time'] = end - start
        start = end

        # add indexes for values that have fuzzy keys that,
        # when matched, have a fuzzy score > 0.
        # we compute and cache all fuzzy scores here.
        #
        # this loop quickly dominate the runtime of correlate
        # once you use even only a couple fuzzy keys per value.
        # it may not look it, but this code has been extensively
        # hand-tuned for speed.
        for fuzzy_type, fuzzy_keys_a in all_fuzzy_keys_a.items():
            fuzzy_keys_b = all_fuzzy_keys_b.get(fuzzy_type)
            if not fuzzy_keys_b:
                continue

            # technically we should check to see if we've cached the fuzzy score already.
            # however, it's rare that any actually reuses a fuzzy key.
            # it's definitely faster to just make the redundant computations
            # without checking in the cache first.
            for key_a in fuzzy_keys_a:
                score_cache_a = fuzzy_score_cache[key_a]
                indexes_a = a._key_to_index[key_a][0]
                for key_b in fuzzy_keys_b:
                    fuzzy_score = key_a.compare(key_b)
                    assert 0 <= fuzzy_score <= 1
                    score_cache_a[key_b] = fuzzy_score
                    if fuzzy_score:
                        for index_a in indexes_a:
                            all_indexes.update([(index_a, index_b) for index_b in b._key_to_index[key_b][0]])

        end = time.perf_counter()
        statistics['pass 2 fuzzy indexes time'] = end - start

        all_indexes = list(all_indexes)
        all_indexes.sort()

        end = time.perf_counter()
        statistics['pass 2 time'] = end - pass_start
        # self.print(f"[pass 2 time: {statistics['pass 2 time']}]") #debug
        # self.print() #debug

        #
        # pass 3
        #
        # self.print("[pass 3: compute fuzzy key match score subtotals]") #debug

        # the third pass computes fuzzy matches.
        # but their scores are incomplete.
        # we can't compute the final fuzzy scores in the first pass,
        # because we don't yet know the cumulative score for each fuzzy key.
        # those cumulative scores are stored in fuzzy_prepass_results.
        #

        pass_start = end

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

        all_correlations = []
        class Correlations:
            def __init__(self, id):
                self.id = id
                self.matches = []
                all_correlations.append(self)

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
                absolute_correlations = Correlations("AbsoluteRanking")
            if ranking in (RelativeRanking, BestRanking):
                relative_correlations = Correlations("RelativeRanking")

            ranking_range_a = a._highest_ranking - a._lowest_ranking
            ranking_range_b = b._highest_ranking - b._lowest_ranking
            widest_ranking_range = max(ranking_range_a, ranking_range_b)
            one_minus_ranking_factor = 1.0 - ranking_factor
        else:
            correlations = Correlations("RankingNotUsed")


        # we save up the log from our processing in pass 3
        # and dump it into pass 4.
        # this means all the per-match processing log prints
        # are in one place.  you're welcome!
        # match_log = defaultdict_list() #debug
        # def match_print(indexes, *a, sep=" "): #debug
            # s = sep.join(str(x) for x in a).rstrip() #debug
            # match_log[indexes].append(s) #debug

        # index_padding_length = math.floor(math.log10(max(len(dataset.values) for dataset in self.datasets))) #debug

        pass_start = time.perf_counter()
        fuzzy_prepass_results = []

        fuzzy_semifinal_matches = []

        for indexes in all_indexes:
            index_a, index_b = indexes

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

            # print_header = True #debug
            for fuzzy_type in fuzzy_types_in_common:

                fuzzy_matches = []

                for subkey_a in fuzzy_a[fuzzy_type]:
                    for subkey_b in fuzzy_b[fuzzy_type]:
                        fuzzy_score = None
                        for pair in itertools.product(subkey_a, subkey_b):
                            tuple_a, tuple_b = pair
                            key_a, weight_a, round_a = tuple_a
                            key_b, weight_b, round_b = tuple_b

                            if fuzzy_score is None:
                                fuzzy_score = fuzzy_score_cache[key_a][key_b]
                                if fuzzy_score <= 0:
                                    break
                                fuzzy_score_cubed = fuzzy_score ** 3

                            # if print_header: #debug
                                # print_header = False #debug
                                # match_print(indexes, f"    fuzzy key matches") #debug
                            # match_print(indexes, f"        {key_a=} x {key_b=} = {fuzzy_score=}") #debug

                            weighted_score = (weight_a * weight_b) * fuzzy_score_cubed

                            if round_a < round_b:
                                sort_by = (fuzzy_score, -round_a, -round_b)
                            else:
                                sort_by = (fuzzy_score, -round_b, -round_a)

                            # match_print(indexes, f"            weights=({weight_a}, {weight_b}) {weighted_score=}") #debug
                            item = CorrelatorMatch(tuple_a, tuple_b, fuzzy_score)
                            item.scores = (fuzzy_score, weighted_score)
                            item.sort_by = sort_by
                            fuzzy_matches.append(item)

                if len(fuzzy_matches) == 0:
                    continue

                if len(fuzzy_matches) > 1:
                    fuzzy_matches.sort(key=lambda x : x.sort_by)
                    fuzzy_boiler = MatchBoiler(fuzzy_matches)
                    # fuzzy_boiler.name = f"fuzzy boiler {indexes=}" #debug
                    # def fuzzy_boiler_print(s=""): match_print(indexes, s) #debug
                    # fuzzy_boiler.print = fuzzy_boiler_print #debug
                    fuzzy_matches = fuzzy_boiler()[0]

                for item in fuzzy_matches:
                    fuzzy_score, tuple_a, tuple_b = item
                    fuzzy_key_cumulative_score_a[tuple_a] += fuzzy_score
                    fuzzy_key_cumulative_score_b[tuple_b] += fuzzy_score
                    fuzzy_score, weighted_score = item.scores
                    fuzzy_semifinal_matches.append( (fuzzy_score, weighted_score, tuple_a, tuple_b) )

            # plural = "" if len(fuzzy_semifinal_matches) == 1 else "s" #debug
            # match_print(indexes, f"        {len(fuzzy_semifinal_matches)} fuzzy score{plural}.") #debug

            if not fuzzy_semifinal_matches:
                fuzzy_prepass_results.append(empty_tuple)
                continue

            fuzzy_prepass_results.append(fuzzy_semifinal_matches)
            fuzzy_semifinal_matches = []

        end = time.perf_counter()
        delta = end - pass_start
        statistics["pass 3 time"] = delta
        # self.print(f"[pass 3 time: {statistics['pass 3 time']}]") #debug
        # self.print() #debug


        # pass 4
        #
        # self.print("[pass 4: compute all match scores]") #debug
        # self.print() #debug

        # this pass does all the rest of the per-match work.
        # it computes:
        #   * all exact matches and scores,
        #   * the final scores for fuzzy matches,
        #   * the score_ratio_bonus,
        #   * and any modification based on ranking_factor or ranking_bonus.
        # its output is stored in all_correlations,
        # a list of Correlations objects used by the third (and final) pass.

        pass_start = end

        for indexes, fuzzy_semifinal_matches in zip(all_indexes, fuzzy_prepass_results):
            index_a, index_b = indexes

            # cumulative_base_score is the total score of actual matched keys for these indexes
            # this is used in the computation of score_ratio_bonus.  this is the pre-weight score.
            cumulative_base_score = 0

            # self.print(f"match {index_a} x {index_b} :") #debug
            # self.print(f"    value a: index {index_a:>{index_padding_length}} {self.dataset_a.values[index_a]}") #debug
            # self.print(f"    value b: index {index_b:>{index_padding_length}} {self.dataset_b.values[index_b]}") #debug

            exact_scores = []

            rounds_a = exact_rounds_a[index_a]
            rounds_b = exact_rounds_b[index_b]

            # i = 0 #debug
            for round_a, round_b in zip(rounds_a, rounds_b):
                # self.print(f"    exact round {i+1}") #debug
                keys_a, weights_a = round_a
                keys_b, weights_b = round_b

                keys_intersection = keys_a & keys_b
                if not keys_intersection:
                    # self.print("        no intersecting keys, early-exit.") #debug
                    break

                try:
                    # why bother? this removes the last little bit of randomness from the algorithm.
                    keys_intersection = tuple(sorted(keys_intersection))
                except TypeError:
                    pass

                cumulative_base_score += len(keys_intersection) * 2

                # sorted_a = "{" + ", ".join(list(sorted(keys_a))) + "}" #debug
                # sorted_b = "{" + ", ".join(list(sorted(keys_b))) + "}" #debug
                # sorted_intersection = "{" + ", ".join(list(sorted(keys_intersection))) + "}" #debug
                # self.print(f"        keys in a {sorted_a}") #debug
                # self.print(f"        keys in b {sorted_b}") #debug
                # self.print(f"        keys in common {sorted_intersection}") #debug

                # weights = [dataset._rounds[0].map[key] for dataset in self.datasets]

                old_len = len(exact_scores)
                for key in keys_intersection:
                    score = weights_a[key] * weights_b[key]
                    # self.print(f"        score for matched key {key!r} =  {score} ({weights_a[key]=} * {weights_b[key]=})") #debug
                    if score:
                        exact_scores.append(score)

                if old_len == len(exact_scores):
                    # self.print("        no scores, early-exit.") #debug
                    break

                # i += 1 #debug

            # dump match log here
            # _l = match_log[indexes] #debug
            # if _l: #debug
                # _s = "\n".join(_l) #debug
                # self.print(_s) #debug
            # self.print() #debug

            # if fuzzy_semifinal_matches: #debug
                 # self.print("    finalize fuzzy scores:") #debug
            for t2 in fuzzy_semifinal_matches:
                fuzzy_score, weighted_score, tuple_a, tuple_b = t2
                # key_a = tuple_a[0] #debug
                # key_b = tuple_b[0] #debug
                # self.print(f"        {key_a=}") #debug
                # self.print(f"        {key_b=}") #debug
                hits_in_a = fuzzy_key_cumulative_score_a[tuple_a]
                hits_in_b = fuzzy_key_cumulative_score_b[tuple_b]
                score = weighted_score / (hits_in_a * hits_in_b)
                cumulative_base_score += fuzzy_score * 2
                # self.print(f"        {score=} = {weighted_score=} / ({hits_in_a=} * {hits_in_b=})") #debug
                # self.print() #debug
                exact_scores.append(score)

            exact_scores.sort()
            score = sum(exact_scores)

            # self.print(f"    {score} subtotal score for match, before bonuses and ranking") #debug

            if score_ratio_bonus:
                bonus = (
                    (score_ratio_bonus * cumulative_base_score)
                    / (total_keys_a[index_a] + total_keys_b[index_b])
                    )
                # self.print(f"    hit ratio {bonus=} = {score_ratio_bonus=} * {cumulative_base_score=}) / ({total_keys_a[index_a]=} + {total_keys_b[index_b]=})") #debug
                score += bonus

            if not using_rankings:
                # self.print(f"    {score} final score") #debug
                # self.print() #debug
                correlations.add(index_a, index_b, score)
                continue

            # self.print(f"    {score} pre-ranking score") #debug
            absolute_score = relative_score = score
            ranking_a = self.dataset_a._ranking(index_a)
            ranking_b = self.dataset_b._ranking(index_b)

            if (ranking_a is not None) and (ranking_b is not None):
                relative_a = ranking_a / ranking_range_a
                relative_b = ranking_b / ranking_range_b
                relative_distance_factor = 1 - abs(relative_a - relative_b)

                absolute_distance_factor = 1 - (abs(ranking_a - ranking_b) / widest_ranking_range)

                # self.print() #debug
                # self.print(f"    ranking factors:") #debug
                # self.print(f"        {absolute_distance_factor=}") #debug
                # self.print(f"        {relative_distance_factor=}") #debug

                if ranking_factor:
                    # self.print(f"    applying {ranking_factor=}") #debug
                    absolute_score *= one_minus_ranking_factor + (ranking_factor * absolute_distance_factor)
                    relative_score *= one_minus_ranking_factor + (ranking_factor * relative_distance_factor)
                elif ranking_bonus:
                    # self.print(f"    applying {ranking_bonus=}") #debug
                    absolute_score += ranking_bonus * absolute_distance_factor
                    relative_score += ranking_bonus * relative_distance_factor
            else:
                # if we don't have valid ranking for both sides,
                # and ranking_factor is in use,
                # we need to penalize this match so matches with ranking info are worth more
                if ranking_factor:
                    # self.print(f"    incomplete ranking information for this match, applying ranking penalty") #debug
                    # self.print(f"    applying {ranking_factor=}") #debug
                    absolute_score *= one_minus_ranking_factor
                    relative_score *= one_minus_ranking_factor

            # self.print(f"    final scores:") #debug
            # self.print(f"        {absolute_score=}") #debug
            # self.print(f"        {relative_score=}") #debug
            # self.print() #debug

            if absolute_correlations is not None:
                absolute_correlations.add(index_a, index_b, absolute_score)
            if relative_correlations is not None:
                relative_correlations.add(index_a, index_b, relative_score)

        end = time.perf_counter()
        delta = end - pass_start
        statistics["pass 4 time"] = delta
        # self.print(f"[pass 4 time: {statistics['pass 4 time']}]") #debug
        # self.print() #debug


        #
        # pass 5
        #
        # self.print("[pass 5: boil down matches (for every ranking being considered)]") #debug

        # this final pass iterates over all Correlations objects:
        #
        # if the user specified a specific approach, or isn't using rankings,
        #   there will only be one Correlations object.
        # if the user is using rankings and didn't specify an approach,
        #   there will be two Correlations objects.
        #   one represents absolute ranking,
        #   and the other represents relative ranking.
        #
        # this pass is where we use the "match boiler" to boil down
        # all our matches obeying reuse_a and reuse_b.

        pass_start = end
        results = []

        match_boiler_time = 0
        for correlations in all_correlations:
            matches = correlations.matches
            sort_matches(matches)
            # throw away matches with score < minimum_score
            for i, item in enumerate(matches):
                if item.score > minimum_score:
                    matches = matches[i:]
                    break
            else:
                matches = []

            total_matches = len(matches)
            start = time.perf_counter()
            boiler = MatchBoiler(matches=matches, reuse_a=reuse_a, reuse_b=reuse_b)
            # boiler.print = self.print #debug
            matches, seen_a, seen_b = boiler()
            end = time.perf_counter()
            delta = end - start
            match_boiler_time += delta

            cumulative_score = sum(item.score for item in matches)

            if matches:
                # clipped_score_integer, dot, clipped_score_fraction = str(cumulative_score).partition(".") #debug
                # clipped_score = f"{clipped_score_integer}{dot}{clipped_score_fraction[:4]}" #debug
                # self.print(f"    correlations for ranking approach {correlations.id}:") #debug
                # self.print(f"        cumulative_score {clipped_score}, {len(matches)} matches, {len(seen_a)} seen_a, {len(seen_b)} seen_b") #debug
                results.append((cumulative_score, matches, total_matches, seen_a, seen_b, correlations))

        end = time.perf_counter()
        statistics["pass 5 match boiler time"] = match_boiler_time
        statistics["pass 5 time"] = end - pass_start
        # self.print(f"[pass 5 time: {statistics['pass 5 time']}]") #debug
        # self.print() #debug

        #
        # pass 6
        #
        # self.print("[pass 6: choose highest-scoring ranking and finalize result]") #debug

        pass_start = end

        if not results:
            matches = []
            total_matches = 0
            unmatched_a = list(self.dataset_a.values)
            unmatched_b = list(self.dataset_b.values)
            ranking_used = CorrelatorRankingApproach.RankingNotUsed
            # self.print(f"    no valid results!  returning 0 matches.  what a goof!") #debug
        else:
            results.sort(key=lambda x: x[0])
            # self.print(f"    all ranking results:") #debug
            # for cumulative_score, matches, total_matches, seen_a, seen_b, correlations in results: #debug
                # self.print(f"        {correlations.id=} {cumulative_score=}") #debug
            # use the highest-scoring correlation
            cumulative_score, matches, total_matches, seen_a, seen_b, correlations = results[-1]
            # self.print(f"    using rankings result {correlations.id}, cumulative score {cumulative_score}") #debug
            unmatched_a = [value for i, value in enumerate(a.values) if i not in seen_a]
            unmatched_b = [value for i, value in enumerate(b.values) if i not in seen_b]
            ranking_used = correlations.id

        statistics["total matches"] = total_matches
        statistics["ranking used"] = ranking_used
        # self.print() #debug

        for match in matches:
            match.value_a = a.values[match.value_a]
            match.value_b = b.values[match.value_b]

        return_value = CorrelatorResult(matches, unmatched_a, unmatched_b, minimum_score, statistics)
        end = time.perf_counter()
        statistics["pass 6 time"] = end - start
        # self.print(f"[pass 6 time: {statistics['pass 6 time']}]") #debug
        statistics["elapsed time"] = end - correlate_start
        # self.print(f"[correlation done!]") #debug
        # self.print(f"[total elapsed time: {statistics['elapsed time']}]") #debug
        # self.print() #debug
        return return_value
