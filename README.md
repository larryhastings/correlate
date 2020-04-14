# correlate

## A clever brute-force correlator for kinda-messy data

##### Copyright 2019-2020 by Larry Hastings


## Overview

Let's say you have two sets of data that really represent the same data,
just in different forms.
As an example, maybe your first dataset is Wikipedia's list of all episodes of a TV
show, and your second dataset is a directory full of video files of
that TV show.  The episode *"Neurostim"* appears in both datasets but
it's represented differently in each.

Now let's say you want to match them up with each other--you want
to match up the values in the first dataset with their equivalents
in the second dataset. The thing is, it's real-world data--and
it's probably a little messy.  Perhaps the two datasets aren't in
the exact same order.  And while some matches are obvious, others are less so.
Maybe one dataset has some values not present in the other and vice-versa.

What do you do?  Sure, you could correlate the two datasets by hand.
But what if the datasets are really big?
And what do you do if they get updated?  Do you want to update the
correlation by hand too?

**correlate** solves this problem for you.  It correlates values between
two messy but strongly-related datasets.

How it works: you submit your two datasets to
**correlate**, showing it each value and the "keys" that map to that value.
You then set it to work.  It thinks for a while, then produces its best
guess as to how to match the two sets.  And its best guess is... hey, that's
pretty good!

In essense, **correlate** uses the uniqueness of keys as clues to pair up
its matches.  If there's a key present in both datasets, but it only maps
to one value in each dataset, odds are good that those two values
are an excellent match.

That's the basics, but **correlate** supports some advanced features:

* A key mapping can optionally specify a *weight*.

* You can map a key *multiple times.*

* Keys can be *fuzzy keys,* keys that may only partially match each other.

* The order of values can inform the matches.  This is called *ranking.*

### Quick Start

This code:

    import correlate

    c = correlate.Correlator()
    a, b = c.datasets

    a.set("this", "greg")
    a.set("is", "greg")
    a.set("Greg", "greg", weight=5)
    a.set_keys("Carol over here".split(), "carol")
    a.set_keys("My name is Tony".split(), "tony")
    a.set_keys("Hi I'm Steve".split(), "steve", weight=2)

    b.set_keys("gosh my name is Greg".split(), "Greg")
    b.set_keys("Carol is my name".split() , "Carol")
    b.set_keys("Pretty sure I'm still Tony".split(), "Tony")
    b.set_keys("I'm Steve".split(), "Steve")

    result = c.correlate()
    for match in result.matches:
        print(f"{match.score:1.3f} {match.value_a} -> {match.value_b}")

produces this output:

    5.750 greg -> Greg
    3.800 steve -> Steve
    1.286 carol -> Carol
    1.222 tony -> Tony


### A Real-Life Example

There's a podcast I like.  I download it as MP3 files
using an RSS feed, 1990s-style. But the metadata in the RSS
feed is junk--the episode titles are inconsistent,
and the episode numbers are almost wholly absent.

This podcast also has a
list of episodes on its website. This data is *much* cleaner,
including nice proper (unique!) episode numbers.  And it's easily
scraped.  But it's still not perfect.
The two lists of episodes aren't exactly the same, and even the episodes
that are present in both are sometimes reordered.

Obviously, I want to take the MP3s from the RSS feed,
and match them up with the nice clean metadata scraped from the website.
This gets me the best of both worlds.

But there are more than *six hundred* episodes of this
particular podcast!  Matching those by hand would be a *lot* of work.
And we get a new episode every week.
And sometimes they actually add back in old episodes, or update the
metadata on old episodes--changes which would mess up any hand-built
ordering.  And I might want to listen to more than one podcast from
this same website someday!
So I really didn't want to do all of this by hand.

Happily, after applying just a bit of intelligence to the two
datasets, **correlate** did a perfect job.

### Why correlate Works So Well

The insight that inspired **correlate** is this:
unique keys in the two datasets are probably very good matches.
Let's say the key `"egyptian"` maps to value *A1* in `dataset_a`
and value *B1*  in `dataset_b`--and it *only* maps to those two
values.  In that case, *A1* and *B1* are probably a match.

This leads to a virtuous cycle.
Let's say the word `"nickel"` maps to two values in each of the
two datasets: *A1* and *A2*, and *B1* and *B2*.
We could match those four values in two possible ways:
*A1* -> *B1* and *A2* -> *B2*,
or *A1* -> *B2* and *A2* -> *B1*.
But the key `"egyptian"` already showed that *A1* and *B1* are a
good match.  If we've already removed those two values from
consideration, we're left with *A2* -> *B2*.
And now *that* looks like a good match, too.

In short, **correlate** capitalizes on the *relative uniqueness*
of keys.


## Getting Started With correlate

### Requirements

**correlate** requires Python 3.6 or newer.  It has no
other dependencies.

If you want to run the **correlate** test suite,
you'll need to install the `rapidfuzz` package.


### The High-Level Conceptual Model

To correlate two datasets with **correlate**,
you first create a `correlate.Correlator` object.
This object contains two members
`dataset_a` and `dataset_b`; these represent
the two datasets you want to correlate.

You fill each dataset with *keys* and *values*.

A *value* is (nearly) any Python object.
Each value should represent one value from your dataset.
**correlate** doesn't examine your values--they're completely
opaque to **correlate**.

A *key* is a Python object that represents some metadata
about a value.  Keys "map" to values; **correlate** examines
keys, using matching keys in the two datasets to
match up the values between them.

Keys are usually strings--for example, the individual words
from the title of some movie, TV show, song, or book.
But keys don't have to be strings.  Instances of lots of
Python data types can be used as keys.

Once you've filled in the `correlate.Correlator` object
with your data, you call its `correlate()` method.  This
computes the matches.  It returns a
`correlate.CorrelateResult` containing
those matches, and lists of any objects from
the two datasets that didn't get matched.

The matches are returned as a list of `correlator.CorrelatorMatch`
objects.  Each object contains three members:

* `value_a`, a reference to an object from `dataset_a`,

* `value_b`, a reference to an object from `dataset_b`,

* and a floating-point `score`.

Each `CorrelatorMatch` object tells you that
**correlator** thinks that this `value_a`
maps to this `value_b`.  The `score` is a sort of mathematical
confidence level--it's a direct result of the keys and
other metadata you provide to **correlate**.  The list of
matches is sorted by `score`--higher scores first, as higher
scores represent higher confidence in the match.

That's the basics.  But **correlate** supports some very sophisticated
behavior:

* When mapping a key to a value, you may specify an optional *weight*,
which represents the relative importance of this key.  The default
weight is 1.  Higher scores indicate a higher significance; a weight of
2 tells **correlate** that this key mapped to this value is twice as
significant.

* A key can map to a value multiple times.  Each mapping can have its own weight.

* If both datasets are ordered, this ordering can optionally influence the match scores.
**correlate** calls this *ranking.*  Ranking is an attribute of values, not keys.

* Keys can be "fuzzy", meaning two keys can be a partial match rather than a binary yes/no.
Fuzzy keys in **correlate** must inherit from a custom abstract base class called
`correlate.FuzzyKey`.

## Sample Code And infer_mv

If you want to get a feel for what it's like to work with **correlate**,
the package ships with some sample code you can inspect.  Take a look
at the scripts in the `tests` and `utilities` directories.

In particular, `utilities` contains a script called `infer_mv`.
`infer_mv` takes a source directory and a list of files and directories
to rename, and produces a mapping from the former to the latter.
In other words, when you run it, you're saying
"here's a source directory and a list of files and directories to rename.
For each file in the list of things to rename, find the
filename in the source directory that most closely resembles that file,
and rename the file so it's exactly like that other filename from the
source directory."  (If you ask `infer_mv` to rename a directory,
it renames all the files and directories inside that directory, recursively.)

This is useful if, for example, you have a directory where
you've already renamed the files the way you you like them, but then
you get a fresh copy from somewhere.  Simply run `infer_mv` with your
existing directory as the "source directory" and the fresh copy
as the "files".  `infer_mv` will figure out how to rename the
fresh files so they have the filenames how you like them.

Note that `infer_mv` doesn't actually do the work of renaming!
Instead, `infer_mv` prints out a *shell script* that, if executed,
performs the renames.
Why?  It's always a good idea to check over the output of **correlate**
before you commit to it.

You should use `infer_mv` like so:

    % infer_mv ../old_path *
    # look at output, if it's all fine run
    % infer_mv ../old_path * | sh

Or you can direct the output of `infer_mv` into a file, then
edit the file, then execute that.  Or something else!
Whatever works for you!


## Terminology And Requirements

### Values

Values are Python objects that represent individual elements of your two
datasets.  **correlate** doesn't examine values, and it makes very few
demands on them.  Here are the rules for values:

* Values must support `==`.
* Value comparison must be *reflexive,* *symmetric,* *transitive,* and *consistent*.
  For all these examples, `a` `b` and `c` represent values:
    * *reflexive:* A value must always compare as equal to itself.  `a == a` must evaluate to `True`.
    * *symmetric:* If `a == b` is `True`, then `b == a` must also be `True`.
    * *transitive:* If `a == b` is `True`, and `b == c` is `True`, then `a == c` must also be `True`.
    * *consistent:* If `a == b` is `True`, it must always be `True`,
       and if `a == b` is `False` it must always be `False`.

### Keys

Keys are Python objects that **correlate** uses to find matches between
the two datasets.  If a key maps to a value in `dataset_a` and also
a value in `dataset_b`, those two values might be a good match.

Keys must obey all the same rules as values.  In addition,
keys must be *hashable.*

#### Exact Keys

An "exact" key is what **correlate** calls any key that isn't a "fuzzy" key.
Strings, integers, floats, complex, `datetime` objects--they're all fine to use
as **correlate** keys, and instances of many more types too.

When considering matches, exact keys are binary--either they're an exact match
or they don't match at all.  If you need to understand partial matches you'll have
to use "fuzzy" keys.


#### Fuzzy Keys

A "fuzzy" key is a key that supports a special protocol for performing "fuzzy"
comparisons--comparisons where the result can represent imperfect or partial matches.

Technically speaking, a **correlate** "fuzzy" key
is an instance of a subclass of `correlate.FuzzyKey`.  If a key is an instance of
a subclass of that base class, it's a "fuzzy" key, and if it isn't, it's an "exact" key.

Fuzzy keys must follow the rules for keys above.
Also, the type of your fuzzy keys must also obey the same rules as keys;
they must be hashable, they must support `==`,
and their comparison must be reflexive, symmetric, transitive, and consistent.

In addition, fuzzy keys must support a method called `compare` with this signature:
`self.compare(other)`.  `other` will be another fuzzy key of the same type.  Your `compare`
function should return a number between (and including) `0` and `1`, indicating how close
a match `self` is to `other`.  If `compare` returns `1`, it's saying this is a perfect
match, that the two values are identical; if it returns `0`, it's a perfect mismatch,
telling **correlate** that the two keys have nothing in common.

**correlate** requires that `compare` also obey the four mathematical constraints required
of comparisons between keys.  In the following rules, `a` and `b` are fuzzy keys of the
same type.  `compare` must conform to these familiar four rules:

* *reflexive:* `a.compare(a)` must return `1` (or `1.0`).
* *symmetric:* If `a.compare(b)` returns *x*, then `b.compare(a)` must also return *x*.
* *transitive:* If `a.compare(b)` returns *x*, and `b.compare(c)` returns *x*,
  then `a.compare(c)` must also return *x*.
* *consistent:* If `a.compare(b)` returns *x*, it must *always* return *x*.

It's important to note: fuzzy keys of two *different* types are automatically
considered different to each other.  **correlate** won't even bother calling
`compare()` on them--it automatically assigns the comparison a fuzzy score of `0`.
This is true even for subclasses; if you declare `class MyFuzzyNumber(correlate.FuzzyKey)`
and also `class MyFuzzyInteger(MyFuzzyNumber)`,
**correlate** will never compare an instance of `MyFuzzyNumber` and `MyFuzzyKey`
to each other--it automatically assumes they have nothing in common.

(Internally
**correlate** stores fuzzy keys of different types segregated from each other.
This is a vital optimization!)

On a related note, **correlate** may optionally never
*actually* call `a.compare(a)`, either.  That is, if the exact same key
maps to a value in both `dataset_a` and `dataset_b`, **correlate**
is permitted to skip calling `compare()` and instead automatically
assign the comparison a fuzzy score of `1`.  **correlate** currently
does this--but this is not guaranteed,
as it's only a small optimization, and conditions may change.


## API

`Correlator(default_weight=1)`

> The correlator class.  `default_weight` is the weight used
> when you map a key to a value without specifying an explicit weight.

`Correlator.dataset_a`

`Correlator.dataset_b`

> Instances of `Correlator.Dataset` objects representing the two sets of data you want to correlate.  Initially empty.

`Correlator.datasets`

> A list containing the two datasets: `[dataset_a, dataset_b]`


`Correlator.correlate(*,
            minimum_score=0,
            score_ratio_bonus=1,
            ranking=BestRanking,
            ranking_bonus=0,
            ranking_factor=0,
            key_reuse_penalty_factor=1,
            reuse_a=False,
            reuse_b=False)`

> Correlates the two datasets.  Returns a `correlate.CorrelatorResult` object.
>
> `minimum_score` is the minimum permissible score for a match.  It must be
> greater than or equal to 0.
>
> `score_ratio_bonus` specifies the weight of a bonus awarded to a match based on the ratio of
> the actual score computed between these two values divided by the maximum possible score.
>
> `ranking` specifies which approch to computing ranking **correlate** should use.
> The default value of `BestRanking` means **correlate** will try all approaches
> and choose the one with the highest cumulative score across all matches.
> Other values include `AbsoluteRanking` and `RelativeRanking`.
>
> `ranking_bonus` specifies the weight of the bonus awarded to a match
> based on the proximity of the two values in their respective datasets, as specified
> by their rankings.  The closer the two values are to the same position in their
> respective datasets, the higher a percentage of the `ranking_bonus` will be awarded.
>
> `ranking_factor` specifies the ratio of the base score of a match that is multiplied
> by the proximity of the two values in their respective datasets.  If you ues `ranking_factor=0.4`,
> then a match only automatically keeps 60% of its original score; some percentage
> of the remaining 40% will be re-awarded based on the proximity of the two values.
>
> (You can't use both a nonzero `ranking_bonus` and a nonzero `ranking_factor` in the
> same correlation.  Pick at most one!)
>
> `key_reuse_penalty_factor` is a multiplier applied to the score calculated
> for a key each time a key is re-mapped to a value.  The second time a key is used,
> its score is multiplied by `key_reuse_penalty_factor`; the third time,
> by `key_reuse_penalty_factor**2`, and so on.
> The default value of 1 means every use of a key gets the same score.
> `key_reuse_penalty_factor` should be greater than or equal to 0, and less than or equal to 1.
>
> `reuse_a` permits values in `dataset_a` to be matched to more than one value in `dataset_b`.
> `reuse_b` is the same but for values in `dataset_b` matching `dataset_a`.
> If you set both reuse flags to True, the `correlate.CorrelatorResult.matches`
> list returned will contain *every* possible match.

`Correlate.Dataset()`

> The class for objects representing a dataset.  Behaves somewhat like
> a write-only dict.

`Correlator.Dataset.set(key, value, weight=default_weight)`

> Adds a new correlation.
>
> You can use `Dataset[key] = value` as a shortcut for `Dataset.set(key, value)`.

`Correlator.Dataset.set_keys(keys, value, weight=default_weight)`

> Map multiple keys to a single value, all using the same weight.
> `keys` must be an iterable containing keys.

`Correlator.Dataset.value(value, *, ranking=None)`

> Annotates a value with extra metadata.  Currently only one metadatum
> is supported: `ranking`.
>
> `ranking` represents the position of this value in the dataset,
> if the dataset is ordered.  `ranking` should be an integer
> representing the ranking; if this value is the 19th in the dataset,
> you should supply `ranking=19`.

`Correlator.str_to_keys(s)`

> A convenience function.
> Converts string `s` into a list of string keys using a reasonable approach.
> Lowercases the string, converts some common punctuation into spaces, then splits
> the string at whitespace boundaries.  Returns a list of strings.


### Getting Good Results Out Of Correlate

Unfortunately, you can't always expect perfect results with **correlate**
every time.  You'll usually have to play with it at least a little.

#### Ranking

Naturally, the first step with **correlate** is to plug in your data.
I strongly encourage you to add ranking information if possible.

If the two datasets are ordered, and equivalent items should appear in
roughly the same place in each of the two datasets, ranking information
can make a *sizeable* improvement in the quality of your matches.
To use ranking information, you set the `ranking` for each value in each dataset
that you can, and specify either `ranking_bonus` or `ranking_factor` when
running `correlate()`.
Which one you use kind of depends on how much confidence you have in the
ordering of your datasets.  If you think your ranking information is pretty
accurate, you should definitely use `ranking_factor`; this exerts a much
stronger influence on the matches.
If you have a low confidence in the ordering of your datasets,
choose `ranking_bonus`, which only provides a little nudge.

#### Minimum Score

Once you've plugged in all your data, you should run the correlation,
print out the result in sorted order with the best
matches on top, then scroll to the bottom and see what the *worst*
5% or 10% of matches look like.

If literally all your matches are already perfect--congratulations!
You're *already* getting good results out of **correlate** and you
can stop reading here!  But if you're not that lucky, you've got more
work to do.

The first step in cleaning up **correlate's** output is usually
to stop it from making bad matches by setting a `minimum_score`.

When you have bad matches, it's usually because the two datasets don't map
perfectly to each other.  If there's a value in `dataset_a` that really
has no good match in `dataset_b`, well, **correlate** doesn't really
have a way of knowing that.   So it may match that value to something
anyway.

Look at it this way: the goal of **correlate** is to find matches between
the two datasets.  If it's made all the good matches it can, and there's
only one item left in each of the the two datasets, and they have *anything*
in common at all, **correlate** will match those two values together
out of sheer desparation.

However!  Bad matches like these tend to have a very low score.
And usually all those bad matches are clumped together
at the bottom.  There'll probably be an inflection point
where the scores drop off significantly and the matches go from good to bad.

This is what `minimum_score` is for.  `minimum_score` tells **correlate**
the minimum permissible score for a match.  When you have a clump of bad
matches at the bottom, you simply set `minimum_score` to be somewhere
between the highest bad match and the lowest good match--and
your problem is solved!

(Technically, **minimum_score** isn't actually the *minimum* score.
It's ever-so-slightly *less* than the lowest
permitted score.  As in, for a match to be considered viable, its score
must be *greater than* **minimum_score.**  The default value for
**minimum_score** is 0, which means **correlate** will keep
any match with a positive score.)

Unfortunately it's hard to predict what to set `minimum_score` to in advance.
Its value really depends on your data set--how many keys you have, how good
the matches are, what weights you're using, everything.  It's much more
straightforward to run the correlation, look over the output, find where the
correlations turn bad, and set a minimum score.  With large data sets there's
generally a sudden and obvious dropoff in score, associated with **correlate**
making poor matches.  That makes it pretty easy: set the minimum score so it
keeps the last good match and forgets the rest.  But there's no predicting what
that score will be in advance--every data set is different, and it's really
an emergent property of your keys and weights--so
you'll have to calibrate it correctly for each correlation you run.

(Sometimes there are good matches mixed in with the bad ones at the bottom.
When that happens, the first step is generally to fix *that,* so that the
bad ones are all clumped together at the bottom.  I can't give any general-purpose
advice on what to do here; all I can say is, start experimenting with changes
to your datasets.  Change your keys, adjust your weights, run the correlation
again and see what happens.  Usually when I do this, I realize something I can
do to improve the data I feed in to **correlate**, and I can fix the problem
externally.)

#### Weights

If you're still not getting the results you want, the next adjustment you
should consider is increasing the weight of
keys that provide a clear signal.  If the datasets you're comparing
have some sort of unique identifier associated with each value--like
an episode number, or release date--you should experiment with giving those
keys a heavier weight.  Heavily-weighted keys like this can help
**correlate** zero in on the best matches right away.

It's up to you what that weight
should be; I sometimes use weights as heavy as 5 for super-important keys,
which means this one single key will have the same weight as 5 normal
keys.  Note that a weight of 5 on the mapping in `dataset_a` and
`dataset_b` means that, if those keys match, they'll have a base score
of 25!  If that key only appears once in each dataset, that will almost
*certainly* result in a match.

But weighting can be a dual-edged sword.  If your data has mistakes
in it, a heavy weighting of this bad data magnifies those mistakes.  One bad
heavily-weighted key on the wrong value can inflate the score of a bad match
over the correct match.  And that can have a domino effect--if *A1* should match
to *B1*, but it get mapped to *B43* instead, that means *B1* is probably
going to get mismatched too.  Which deprives another value of its correct
match.  And so on and so on and so on.

#### Too-Common Keys

Similarly, if there are super-common keys that aren't going to help with
the correlation, consider throwing them away and not even feeding them in as
data.  Keys that map to most or all of the values in a dataset add little
clarity, and will mainly serve just to make **correlate** slower.
I usually throw away the word "The", and the name of the podcast or show.
(When correlating filenames, I may throw away the file extension too.)

Then again, often leaving them in won't hurt anything, and it can occasionally
be helpful!  The way **correlate** works, it considers multiple maps of a
key to a value as different things--if you map the key `"The"` to a value
twice, **correlate** understands that those are two separate mappings.
And if there's only one value in each dataset that has two `"The"` mappings,
that can be a very strong signal indeed.  So it's really up to you.
Throwing away largely-redundant keys is a speed optimization, but it
shouldn't affect the quality of your matches.

(The best of both worlds: for common keys, try throwing away the *first* one.)

#### Check Your Inputs

As always, it's helpful to make sure your code is doing what you intend it to.
Several times I've goofed up the mechanism I use to feed data sets into
**correlate**; for example, instead of feeding in words as keys, I've occasionally
fed in the individual characters in those words as keys.  (Like, instead of
the single key `"booze"`, I accidentally fed in the five keys
`'b'`, `'o'`, `'o'`, `'z'`, and `'e'`.)
However, the **correlate** algorithm works so well,
it still did a shockingly good job!  (Though it was a *lot* slower.)

I've learned to double-check that I'm inputting the mappings and weights I meant
to, with a debugger or with turning on the debug print statements in **correlate**
itself.  Making sure you gave **correlate** the right data can make it not only
much more accurate, it might make it faster too!

#### Normalize Strings

When using strings as keys from real-world sources, I recommend you
*normalize* the strings:
lowercase the strings, remove most or all punctuation, break the strings up into
individual keys at word boundaries.  In the real world, punctuation
and capitalization can both be inconsistent, so throwing it away can help
dispel those sorts of inconsistencies.  **correlate**
provides a utility function called `correlate.str_to_keys()` that does this
for you--but you can use any approach you like.

You might also consider *interning* your strings.  In my limited experimentation
this provided a small but measurable speedup.

#### Sharpen Your Fuzzy Keys

If you're using fuzzy keys, the most important thing you can do is *sharpen
your keys.*  Fuzzy string-matching libraries have a naughty habit of scoring
not-very-similar strings as not *that* much less than almost-exactly-the-same
strings.  If you give that data unaltered to **correlate,** that "everything
looks roughly the same" outlook will be reflected in your final results as
mediocre matches.  In those cases it's best to force your fuzzy
matches to extremes.  The best technique is simply to have a minimum score
for fuzzy maches in these cases.  Squaring or cubing the resulting
score is also a cheap way to attenuate weaker fuzzy scores while preserving
the stronger fuzzy scores.


### What Do These Scores Mean?

The scores you seee in the results are directly related to the data you
gave to **correlate**.  The scores really only have as much or as
little meaning as you assign to them.

If you don't enjoy the unpredictable nature of **correlate** scores,
consider calling `normalize()` on your Correlate result object.
This normalizes the scores as follows: the highest score measured
will be adjusted to 1.0, `minimum_score` will be adjusted to 0.0,
and every other score will be adjusted linearly between those two.

Mathematically:

    score = the original score for this match
    highest_score = highest score of any match
    minimum_score = the minimum_score passed in to correlate()
    delta = highest_score - minimum_score
    normalized_score = (score - minimum_score) / delta



## The Algorithm

> If the implementation is hard to explain, it's a bad idea.
> --*The Zen Of Python* by Tim Peters

At the heart of **correlate** is a brute-force algorithm.  It's what
computer scientists would call an **O**(n²) algorithm.

**correlate** computes every possible "match"--every mapping of a value in
`dataset_a` to a value in `dataset_b` where the two values have keys in common.
For exact keys, it uses set intersections to ignore pairs of values that have
nothing in common, discarding early matches it knows will have a score of 0.
Sadly, it can't do that for fuzzy keys, which is why fuzzy keys tend to
slow down  **correlate** even more.

For each key that matches between the two values, **correlate**
computes a score.  It then adds all those scores together,
computing the final cumulative score for the "match",
which it may modifiy based on the various bonuses and factors.
It then iterates over these scores in sorted order, highest score first.
For every match where neither of the two values have been used
in a match yet, it counts that as a "match" and adds it to the output.
(This assumes `reuse_a` and `reuse_b` are both `False`.  Also, this
is a little bit of an oversimplification; see the section about the
*Match Boiler* below.)

One important detail: **correlate** is 100%
deterministic.  Randomness can creep in around the edges in Python
programs; for example, if you ever iterate over a dictionary,
the order you will see the keys will vary from run to run.
**correlate** eliminates these sources of randomness.
Given the exact same inputs, it performs the same operations
in the same order and produces the same result, every time.

There are a number of concepts involved with how the **correlate**
algorithm works, each of which I'll explain in exhausting detail
in the following sub-sections.

### Streamlined Data

The **correlate** datasets store data in a format designed
to eliminate redundancy and be easy to modify.  But this representation
is inconvenient for performing the actual correlate.  Therefore,
the first step is to reprocess the data into a "streamlined" format.
This is an internal-only implementation detail, and in fact the data
is thrown away at the end of each correlation.  As an end-user you'll
never have to deal with it.  It's only documented here just in case you
ever need to understand the implementation of **correlate**.

This streamlined data representation is an important optimization.
It greatly speeds up computing a match between two values.  And it
only costs a little overhead, compared to all that matching work.
Consider: if you have 600 values in `dataset_a` and 600 values in
`dataset_b`, **correlate** will recompute 1,200 streamlined datasets.
But it'll then use it in as many as 360,000 comparisons!   That's
why precomputing the streamlined format is such a big win.

Speaking of internal representations of data...

### Rounds

If you call **correlate** as follows:

    c = correlate.Correlator()
    o = object()
    c.dataset_a.set('a', o)
    c.dataset_a.set('a', o)

then key `'a'` really *is* mapped to value `o` twice,
and those two mappings can have different weights.
It's best to think of repeated keys like this as actually
being two different keys--identical, but distinct.
It's ike having files with the same filename in two
different directories.  They have the same *filename,* but
they're not the same *file.*

**correlate** calls groups of these multiple mappings *"rounds"*.
A "round" contains all the keys from the Nth time they were
repeated; round 0 contains every key, round 1 contains the second
instances of all the keys that were repeated twice, round 2 contains
all the third instances of all the keys that were repeated three times,
etc.
Rounds are per-value, and there are as
many rounds as the maximum number of redundant mappings of
any single key to any particular value in a dataset.

Consider this example:

    c = correlate.Correlator()
    o = object()
    c.dataset_a.set('a', o, weight=1)
    c.dataset_a.set('a', o, weight=3)
    c.dataset_a.set('a', o, weight=5)
    c.dataset_a.set('b', o)
    c.dataset_a.set('b', o)
    c.dataset_a.set('c', o)

    o2 = object()
    c.dataset_b.set('d', o2)
    c.dataset_b.set('d', o2)
    c.dataset_b.set('e', o2)
    c.dataset_b.set('f', o2)

Here, the value `o` in `dataset_a` would have three rounds:

* Round 0 would contain the keys `{'a', 'b', 'c'}`.
* Round 1 would contain the keys `{'a', 'b'}`.
* Round 2 would contain only one key,`{'a'}`.

And `o2` in `dataset_b` would have only two rounds:

* Round 0 would contain the keys `{'d', 'e', 'f'}`.
* Round 1 would contain only one key,`{'d'}`.

And conceptually the `"a"` in round 0 is a different key
from the `"a"` in round 1, etc.

For exact keys, rounds are directly matched iteratively
to each other; the exact keys in round 0 for a value in
`dataset_a` are matched to the round 0 exact keys for a value in
`dataset_b`, round 1 in `dataset_a` is matched to
round 1 in `dataset_b`, and so on.
If one side runs out of rounds early, you stop; if you compute
the intersection of a round and they have nothing in common,
you stop.

One invariant property: each subsequent round has a subset of
the keys before it.  The set of keys in round **N+1** *must*
be a subset of the keys in round **N**.

What about weights?  Higher weights are sorted to lower rounds.
The weight for a key *k* in round **N-1** *must* be greater than
or equal to the weight of *k* in round **N**.
In the above example, the `'a'` in round 0 has weight 5, in round 1
it has weight 3, and in round 2 it has weight 1.
(It doesn't matter what order you insert them in, **correlate**
internally stores the weights in sorted order.)

Thus, round 0 always contains every exact key mapped to
a particular value, with their highest weights.

Rounds can definitely help find the best matches.  If the
key `"The"` maps to most of your values once,
that's not particularly interesting, and it won't affect the scores
very much one way or another.  But if there's only one
value in each dataset that `"The"` maps to *twice,*
that's a very strong signal indeed!  **correlate** does an
*excellent* job of noticing unique-ness like that and factoring
it into the scoring.



### Scoring Exact Keys

For each match it considers, **correlate** computes the intersection of
the keys that map to each of those two values in the two datasets, then
computes a score based on each of those key matches.
The formula used for scoring matches between exact keys
is the heart of **correlate**, and was the original inspiration for
writing the library in the first place.

**correlate** stores the keys per-round in `set()` objects, and computes
this intersection with the marvelously fast `set.intersection()`.

**correlate** computes the score for an individual key as follows:

    key = a key present in both dataset_a and dataset_b
    value_a = a value from dataset_a that key maps to
    value_b = a value from dataset_b that key maps to
    round_number = which round this key is in
    weight_a = weight of the mapping from key -> value_a in dataset_a in round round_number
    weight_b = weight of the mapping from key -> value_b in dataset_b in round round_number
    values_a = the count of values in dataset_a that this key maps to in round round_number
    values_b = the count of values in dataset_b that this key maps to in round round_number
    score_a = weight_a / values_b
    score_b = weight_b / values_a
    semifinal_score = score_a * score_b * (key_reuse_penalty_factor ** round_number)

This `semifinal_score` is then further adjusted based on ranking information,
if used.  (See below.)

Thus, the fewer values a key maps to in a dataset, the higher it scores.
A key that's only mapped once in each dataset scores 4x
higher than a key mapped twice in each dataset.

This scoring formula has a virtuous-feeling mathematical
property I call *"conservation of score".*  Each key that
you add to a round in a dataset adds 1 to the total cumulatve
score of all possible matches; when you map a key to multiple
values, you divide this score up evenly between those values.
For example, if the key `x` is mapped to three values in `dataset_a`
and four values in `dataset_b`, each of those possible matches
only gets 1/12 of that key's score, and the final cumulative
score for all matches only goes up by 1/12.  So a key always
adds 1 to the sum of all scores across all *possible* matches,
but only increases the actual final score by the amount of
signal it *actually* communicated.

Also, now you see why repeated keys can be so interesting.
They add 1 for *each round* they're in, but that score is only
divided by the number of values they're mapped to *in that round!*

### Fuzzy Keys

Once upon a time, **correlate** was small and beautiful and
marvelously fast.  But that version could only support exact keys.
By the time fuzzy keys were completely implemented and feature-complete
and working great, **correlate** was much more complex and... "practical".
It's because fuzzy keys introduce a lot of complex behavior, resulting in
tricky scenarios that just couldn't happen with exact keys.

Consider this example:

>    Your two datasets represent lists of farms.  Both datasets list
>    animals, but might have generic information ("horse") or might
>    have specifics ("Clydesdale").  You create a fuzzy key subclass called
>    `AnimalKey` that can handle matching these together;
>    `AnimalKey("Horse/Clydesdale")` matches `AnimalKey("Horse")`,
>    though with a score less than 1 because it isn't a perfect match.
>
>    The same farm, *Farm X*, is present in both datasets:
>
>    * In `dataset_a`, the keys `AnimalKey("Horse/Clydesdale")`
>    and `AnimalKey("Horse/Shetland Pony")` map to Farm X.
>
>    * In `dataset_b`, the key `AnimalKey("Horse")` maps to Farm X *twice.*
>
>    Question: should one of the `"Horse"` keys match `"Horse/Clydesdale"`,
>    and the other `"Horse"` key match `"Horse/Shetland Pony"`?
>
>    Of course they should!

The scoring used for fuzzy keys is conceptually the same as the scoring
for exact keys, including the concept of "rounds".  In practice, fuzzy key
scoring is much more complicated; there are some multipliers I elided
in the description for exact keys because they're always 1, and some other
things that are easy to compute for exact keys that we must do the hard way
for fuzzy keys.  (There's a whole section at the end of this document about
the history of fuzzy key scoring in **correlate**, in case you're interested.)

Also, it's reasonable for a single value in a dataset to have multiple fuzzy
keys of the same type, which means that now we could have multiple keys
in one dataset in contention for the same key in the other dataset.
In the above example with farms and horses, **correlate** will need to
compare both `AnimalKey("Horse/Clydesdale")` and `AnimalKey("Horse/Shetland Pony")`
from `dataset_a` to `AnimalKey("Horse")` in `dataset_b`.

But **correlate** doesn't add up every possible fuzzy score generated by a
key; when computing the final score, a fuzzy key is only matched against
one other fuzzy key.  If fuzzy keys *FA1* and *FA2* map to value *VA*
in `dataset_a`, and fuzzy key *FB* maps to value *VB* in `dataset_b`,
**correlate** will consider *FA1* -> *FB* and *FA2* -> *FB*
and only keep the match with the highest score.  This match "consumes"
those two keys, and they can't be matched again.  (Again: when I say "key"
here, I mean "this key in this round".)

Wait!  It gets even *more* complicated!
It's entirely possible for a key in one round in `dataset_a` to be
matched to a key from a *different* round in `dataset_b`, again like the
sample of the farms and horses above.  That's right: fuzzy keys can match
keys from *different rounds!*  Computing proper fuzzy scores thus
requires tracking separately how many reuses of each key
we've used so far so that *key_reuse_penalty_factor* can be computed
properly.  Where exact keys use very precise "rounds", fuzzy keys
require a more dynamic approach.  In essense, an unused key in round *N*
can "survive" to rounds *N+1*.  That's what the above example with
farms and ponies is showing us; in round 0, if `"Horse/Clysedale"` in `dataset_a`
gets matched to `"Horse"` in `dataset_b`, `"Horse/Shetland Pony"`
in `dataset_a` goes unmatched and continues on to round 1.  This also
made scoring more complicated.  (For more on this, check out the test
suite.  There's a regression test that exercises this exact behavior.)

So here's how **correlate** computes fuzzy matches.  For each iteration,
it computes all possible fuzzy matches between all viable keys,
stores the results in a list, sorts the list with highest score first,
and keep the highest-scored fuzzy match between two keys that haven't
been "used" yet.  Every key that doesn't get "used" proceeds on to the
next iteration, if there is one, and if that same key was mapped in that
round too the early one displaces the later one.  If fuzzy key *FKA*
is mapped twice to value *VA*, and the first *FKA* doesn't get
used in round 0, that mapping sticks around to the next iteration,
and the second mapping continues to wait.  Complicated, huh!

(One additional subtle point: the *weights* of these fuzzy key mappings
doesn't influence this aspect of scoring; they're only used in calculating
the semi-final score, below.  **correlate** prefers the *best* matches,
not the *most important* matches.)

At last, here's the scoring algorithm for fuzzy keys:

    value_a = a value from dataset_a
    value_b = a value from dataset_b
    key_a = a fuzzy key in dataset_a that maps to value_a
    key_b = a fuzzy key in dataset_b that maps to value_b
    round_a = the round number for this mapping of key_a -> value_a in dataset_a
    round_b = the round number for this mapping of key_b -> value_b in dataset_b
    weight_a = weight of this mapping from key_a -> value_a in round_a in dataset_a
    weight_b = weight of this mapping from key_b -> value_b in round_b in dataset_b
    fuzzy_score = the result of key_a.compare(key_b)
    cumulative_a = the cumulative score of all successful matches between key_a and all fuzzy keys in dataset_b
    cumulative_b = the cumulative score of all successful matches between key_b and all fuzzy keys in dataset_a
    reuse_penalty_a = key_reuse_penalty_factor ** round_a
    reuse_penalty_b = key_reuse_penalty_factor ** round_b
    score_ratio_a = (fuzzy_score * reuse_penalty_a) / cumulative_a
    score_ratio_b = (fuzzy_score * reuse_penalty_b) / cumulative_b
    unweighted_score = fuzzy_score * score_ratio_a * score_ratio_b
    score_a = weight_a * unweighted_score_a
    score_b = weight_b * unweighted_score_b
    semifinal_score = score_a * score_b

`cumulative_a` is the sum of all `fuzzy_score` scores for matches using `key_a`.
`unweighted_score` is used when choosing which matches to keep per-round.
`semifinal_score` is the actual score added to the total for this match.
Again, this `semifinal_score` is further permuted by ranking, if used.

It's hard to see it in all that messy math, but fuzzy keys maintain
*"conservation of score"* too.  The total score contributed by a fuzzy key
across all possible matches is guaranteed to be no less than 0 and
no more than 1.  But the amount of score it actually contributes
to the final cumulative score is dependent on how many of those
matches are actually used.  A fuzzy key that, when matched,
always produced a `fuzzy_score` of 1 would behave identically
to an exact key with respect to *"conservation of score"*.


### Score Ratio Bonus

There's a "bonus" score calculated using `score_ratio_bonus`.  It's scored for the
overall mapping of a value in `dataset_a` to a value in `dataset_b`.
This bonus is one of the last things computed for a match, just before ranking.

The bonus is calculated as follows:

    value_a = a value from dataset_a
    value_b = a value from dataset_b
    actual_a = total actual score for all keys that map to value_a in dataset_a
    actual_b = total actual score for all keys that map to value_b in dataset_b
    possible_a = total possible score for all keys that map to value_a in dataset_a
    possible_b = total possible score for all keys that map to value_b in dataset_b
    bonus_weight = score_ratio_bonus * (actual_a + actual_b) / (possible_a + possible_b)

This bonus calculated with `score_ratio_bonus` clears up the
ambiguity when the set of keys mapping to one value is a subset of the keys
mapping to a different value in the same dataset.  The higher percentage
of keys that match, the larger this bonus will be.

Consider this example:

    c = correlate.Correlator()
    c.dataset_a.set('breakin', X)

    c.dataset_b.set('breakin', Y)
    c.dataset_b.set_keys(['breakin', '2', 'electric', 'boogaloo'], Z)

Which is the better match, `X->Y` or `X->Z`?
In early versions of **correlate**, both matches got the exact same score.
So it was the luck of the draw as to which match **correlate** would choose.
`score_ratio_bonus` disambiguates this scenario.  It awards a larger bonus
to `X->Y` than it does to `X->Z`,  because a higher percentage of the keys
matched between `X` and `Y`.
That small boost is usually all that's needed to let **correlate**
disambiguate these situations and pick the correct match.

Two things to note.  First, when I say "keys", this is another situation
where the same key mapped twice to the same value is conceptually considered
to be two different keys.
In the example in the **Rounds** subsection above, where `value_a` is `o` and
`value_b` is `o2`, `possible_a` would be 6 and `possible_b` would be 4.

Second, the scores used to compute `actual` and `possible` are *unweighted.*
If a match between two fuzzy keys resulted in a fuzzy score of `0.3`,
that adds `0.3` to both `actual_a` and `actual_b`, but each of those fuzzy
keys adds `1.0` to `possible_a` and `possible_b` respectively.
All modifiers, like weights and `key_reuse_penalty_factor`,
are ignored when computing `score_ratio_bonus`.


### Choosing Which Matches To Keep: The "Match Boiler"

As mentioned previously, **correlate** iterates over all the matches
sorted by score, and keeps the matches with the highest score where
neither `value_a` nor `value_b` has been matched yet.

Actually that's no longer quite true.
Late in development of **correlate**, I realized there was a small
problem lurking with this approach.  Happily it had a relatively
easy fix, and the fix didn't make **correlate** any slower in the
general case.

Here's the abstract problem: if you're presented with a list of match
objects called `matches`,
where each item has three attributes `value_a`, `value_b`, and `score`,
how would you compute an optimal subset of `matches` such that:

* every discrete value of `value_a` and `value_b` appears only once, and
* the sum of the `score` attributes is maximized?

Finding the perfectly optimal subset would be expensive--not
quite `O(N**2)` but close.  It'd require a brute-force approach,
where, for every item in `matches` that shared a value of `value_a` or
`value_b` with another item, you'd have to run an experiment to
"look ahead" and see what happens if you chose that item.  You
compute the resulting score for each of these items, then
keep the item that resulted in the highest cumulative score.

**correlate** needs to solve this problem in two different contexts:

* when processing the list of fuzzy matches produced during each "round" of fuzzy matching, and
* when processing the overall list of matches computed between `dataset_a` and `dataset_b`
  at the end of the correlation process.

But **correlate** can't use this hypothetical "optimal" algorithm,
because it'd take too long--you probably want your correlation
to finish before our sun turns into a red giant.
Instead, **correlate** used a considerably
cheaper "greedy" algorithm.  As already described several times:
**correlate** sorts
the list of matches by `score`, then iterates down the list highest
to lowest.  For every item, if we haven't already "kept" another item
with the same `value_a` or `value_b`, "keep" this item in the `results`
list, and remember the `value_a` and `value_b`.

This approach completes in linear time.  In theory, it's not guaranteed
to produce optimal results.  In practice, with real-world data, it should.
Except there *is* a plausible problem lurking in this approach!

Consider: what if two values in the list are both viable, and they have the
*same* score, and they have either `value_a` or `value_b` in common?  It's
ambiguous as to which match **correlate** will choose.  But choosing the
wrong one *could* result in objectively less-than-optimal scoring.

Here's a specific example:

* `dataset_a` contains fuzzy keys `fka1` and `fka2`.
* `dataset_b` contains fuzzy keys `fkbH` and `fkbL`.
  Any match containing `fkbH` has a higher score than any match containing `fkbL`.
  (H = high scoring, L = low scoring.)
* The matches`fka1->fkbH` and `fka2->fkbH` have the same score.
* The match `fka1->fkbL` has a lower score than `fka2->fkbL`.

**correlate** should prefer `fka2->fkbL` to `fka1->fkbL`.
But it can only pick that match if it previously picked `fka1->fkbH`.
And there's no guarantee that it would!  If two items in the list have
the same score, it's ambiguous which one **correlate** would choose.
To handle this properly it needs to look ahead and experiment.

My solution for this is what I call the "match boiler", or the "boiler"
for short.  The boiler uses a hybrid approach: it uses the greedy linear
algorithm when scores are unique.  If it encounters a run of items
with matching scores, and where any of those items have `value_a` or
`value_b` in common, it recursively tries the experiment where it keeps
each of those items in turn.  It does the look-ahead, and sums the score
from each recursive experiment, then keeps the experiment with the highest
score.

With the "match boiler" in place, **correlate** seems to produce optimal
results even in these rare ambigous situations.

(Using the boiler to analyze fuzzy rounds got pretty complicated!
It had to support a callback each time it kept a value, which let
the fuzzy keys submit new matches for consideration from subsequent
rounds.)


Even with the boiler, you can still contrive scenarios where **correlate**
will produce arguably sub-optimal results.  If `a1` and `a2` are values
in `dataset_a`, and `b1` and `b2` are values in `dataset_b`, and the
matches have these scores:

    a1->b1 == 10
    a1->b2 == 9
    a2->b1 == 8
    a2->b2 == 1

In this scenario, the boiler will pick `a1->b1`, which means it's
left with `a2->b2`.  Total score: 11.  But if it had picked `a1->b2`,
that means it would get to pick `a2->b1`, and the total score would be 17!
Is that better?  In an abstract, hypothetical scenario like this, it's
hard to say for sure.

In practice I don't think this is really a problem.  Handling the
ambiguous scenario where items had identical scores is already
"gilding the lily", considering how rare it happens with real-world data.
Anyway, when would real data behave in this contrived way?  How
could `a1` score so highly against `b1` and `b2`, but `a1` scores
high against `b1` but low against `b2`?
This scenario simply isn't realistic, and fixing it would likely be
computationally expensive for the general case.  So it's just not
worth it.  Relax, YAGNI.


### Ranking

Ranking information can help a great deal.
If a value in `dataset_a` is near the beginning, and the order
of values is significant, then we should prefer matching it to values
in `dataset_b` near the beginning too.  Matching the first
value in `dataset_a`
against the last value in `dataset_b` is probably bad.

Conceptually it works as follows: when scoring a match,
measure the distance between
the two values and let that distance influence the score.  The closer
the two values are to each other, the higher the resulting score.

But how do you compute that delta?  What do the ranking numbers mean?
**correlate** supports two possible interpretations
of the rankings, what we'll call *absolute* and *relative* ranking.
These two approaches differ in how they compare the ranking numbers,
as follows:

* *Absolute* ranking assmes the ranking numbers are the same
  for both datasets.  `ranking=5` in `dataset_a` is a perfect
  match to `ranking=5` in `dataset_b`.
* *Relative* ranking assumes that the two datasets represent the
  same range of data, and uses the ratio of the ranking of a value
  divided by the highest ranking set in that dataset to compute
  its relative position.  If the highest ranking we saw in a
  particular dataset was `ranking=150`,
  then a value that has `ranking=12` set is calculated to be 8%
  of the way from the beginning to the end.  This percentage
  is calculated similarly for both datasets, and the distance
  between two values is the distance between these two percentages.

For example, if `dataset_a` had 100 items ranked 1 to 100,
and `dataset_b` had 800 items ranked 1 to 800,
a value to `dataset_a` with `ranking=50` in *absolute* ranking
would be considered closest to a value in `dataset_b` with `ranking=50`,
but when using *relative* ranking
it'd be considered closest to a value in `dataset_b` with `ranking=400`.

Which one does **correlate** use?  It's configurable with the `ranking`
parameter to `correlate()`.  By default it uses "best" ranking.
"Best" ranking means **correlate** will compute scores using *both*
methods and choose the approach with the highest overall score.
You can override this by supplying a different value to `ranking`
but this shouldn't be necessary.  (Theoretically it should be faster
to use a specific ranking approach.  Unfortunately this hasn't been
optimized yet, so using only one ranking doesn't really speed things up.)


Ranking is the last step in computing the score of a match.
As for how ranking affects the score, it depends on whether you
use `ranking_bonus` or `ranking_factor`.

Both approaches start with these four calculations:

    semifinal_scores_sum = sum of all "semifinal" scores above
    ranking_a = the ranking value computed for value_a
    ranking_b = the ranking value computed for value_b
    ranking_score = 1 - abs(ranking_a - ranking_b)

`ranking_bonus` is then calculated per-match as follows:

    bonus = ranking_score * ranking_bonus
    final_score = semifinal_scores_sum + bonus

`ranking_factor` is also calculated per-match, as follows:

    unranked_portion = (1 - ranking_factor) * semifinal_scores_sum
    ranked_portion = ranking_factor * semifinal_scores_sum * ranking_score
    final_score = unranked_portion + ranked_portion

(If you don't use either, the final score for the match is effectively
`semifinal_scores_sum`.)

Obviously, `ranking` must be set on both values in both datasets to
properly compute `ranking_score`.  If it's not set on *both* values
being considered for a match, **correlate** still applies
`ranking_bonus` or `ranking_factor` as usual, but it skips the
initial four calculations and just uses a `ranking_score` of 0.


## Final Random Topics

### Debugging

When all else fails... what next?

**correlate** can optionally produce an enormous amount of debug output.
The main feature is showing every match it tests, and the score arrived
at for that match, including every step along the way.  This log output
quickly gets very large; even a comparison of 600x600 elements will produce
tens of megabytes of output.

Unfortunately, producing this much debugging output incurred a measurable
performance penalty--even when you had logging turned off!  It was mostly
in computing the "f-strings" for the log, but also simply the calls to
the logging functions added overhead too.

My solution: by default, each of the debug print statements
is commented out.
**correlate** ships with a custom script preprocessor called
`debug.py` that can toggle debugging on and off, by uncommenting and
re-commenting the debug code.

How does it know which lines to uncomment?  Each line of the logging-only
code ends with the special marker "`#debug`".

To turn on this logging, run the `debug.py` script in the same directory
as **correlate's** `__init__.py` script.  Each time you run it, it'll
toggle the debug print statements.
Note that the debug feature in **correlate** requires Python 3.8 or higher,
because it frequently uses the beloved "equals sign inside f-strings" syntax.

By default the logging is sent to stdout.  If you want to override where
it's sent, write your own `print` function, and assign it to your
`Correlator` object before calling `correlate()`.

The format of the log is undocumented and subject to change.  Good luck!
The main thing you'll want to do is figure out the "index" of the values
in datasets a and b that you want to compare, then search for `" (index_a) x (index_b) "`.
For example, if the match you want to see is between value index 35 in `dataset_a`
and value index 51 in `dataset_b`, search in the log for `" 35 x 51 "`.
(The leading and trailing spaces means your search will skip over,
for example, `235 x 514`.)


### Alternate Fuzzy Scoring Approaches That Didn't Work

The math behind fuzzy scoring is a bit surprising, at least to me.
If you boil down the formula to its constituent factors,
you'll notice one of the factors is `fuzzy_score` *cubed.*
Why is it *cubed?*

The simplest answer: that's the first approach that worked
properly.  To really understand why, you'll need to understand the
history of fuzzy scoring in **correlate**--all the approaches
I tried first that *didn't* work.

Initially, the score for a fuzzy match was simply the fuzzy score
multiplied by the weights and `key_reuse_penalty_factor`.
This was always a dumb idea; it meant fuzzy matches had *way* more
impact on the score than they should have.  This was particularly
true when you got down to the last 10% or 20% of your matches,
by which point the score contributed by exact keys had
fallen off a great deal.  This approach stayed in for what is,
in retrospect, an embarassingly long time; I'd convinced myself
that fuzzy keys were innately more *interesting* than exact keys,
and so this comparative importance was fitting.

Once I realized how dumb that was, the obvious approach was to score
them identically to exact keys--divide the fuzzy score by the product
of the number of keys this *could* have matched against in each
of the two datasets.  This was obviously wrong right away.
In the "YTJD" test, every value had the same fuzzy keys, depending
on the test: every value always had a fuzzy date key, and depending
on the test it might have a fuzzy title key and/or a fuzzy episode number
key too.  So each of the 812 values in the first dataset had one
fuzzy key for each type, and each of the 724 values in the second dataset
did too.  Even if we got a perfect fuzzy match, the maximum score
for a fuzzy match was now `1.0 / (812 * 724)` which is `0.0000017`.  So now
we had the opposite problem: instead of being super important, even a perfect
fuzzy match contributed practically nothing to the final score.

After thinking about it for a while,
I realized that the exact key score wasn't *really* being
divided by the number of *keys* in the two datasets, per se;
it was being divided by the total possible *score* contributed
by that key in each of the two datasets.  So instead of
dividing fuzzy scores by the number of keys, they should be divided
by the cumulative fuzzy score of all matches involving those two keys.
That formula looks like
`fuzzy_score / (sum_of_fuzzy_scores_for_key_in_A * sum_of_fuzzy_scores_for_key_in_B)`.

This was a lot closer to correct!  But this formula had a glaring new problem.
Let's say that in your entire correlation, `dataset_a` only had one
fuzzy key that maps to a single value,
and `dataset_a` only had one fuzzy key that also only maps to a single value.
And let's say the fuzzy score you get from matching those two keys
is `0.000001`--a really terrible match.
Let's plug those numbers into our formula, shall we.  We get `0.000001 / (0.000001 * 0.000001)`
which is `1000000.0`.  A million!  That's crazy!  We've taken an absolutely
terrible fuzzy match and inflated its score to be nonsensically high.
Clearly that's not right.

This leads us to the formula that actually works.  The insight here
is that the same formula needs to work identically for exact keys.
If you take this formula and compute it where every `fuzzy_score`
is 1 (or 0), it produces the same result as the formula for exact keys.
So the final trick is that we can multiply by `fuzzy_score` wherever we need
to, because multiplying by 1 doesn't change anything.  That means
the resulting formula will still be consistent with the exact keys
scoring formula.  And what worked was the formula where we multiply by
`fuzzy_score` three times!

Here again is the formula used to compute the score for a fuzzy match,
simplified to ignore weights and rounds:

    value_a = a value from dataset_a
    value_b = a value from dataset_b
    key_a = a fuzzy key in dataset_a that maps to value_a
    key_b = a fuzzy key in dataset_b that maps to value_b
    fuzzy_score = the result of key_a.compare(key_b)
    cumulative_a = the cumulative score of all successful matches between key_a and all fuzzy keys in dataset_b
    cumulative_b = the cumulative score of all successful matches between key_b and all fuzzy keys in dataset_a
    score_ratio_a = fuzzy_score / cumulative_a
    score_ratio_b = fuzzy_score / cumulative_b
    unweighted_score = fuzzy_score * score_ratio_a * score_ratio_b

The final trick really was realizing what `score_ratio_a` represents.
Really, it represents the ratio of how much *this* fuzzy match for `key_a`
contributed to the sum of *all* fuzzy matches for `key_a`
across all successful matches in `dataset_a`.

### Why correlate Doesn't Use The Gail-Shapley Algorithm

A friend asked me if this was isomorphic to the Stable Matching Problem:

https://en.wikipedia.org/wiki/Stable_matching_problem

Because, if it was, I might be able to use the Gail-Shapley algorithm:

https://en.wikipedia.org/wiki/Gale%E2%80%93Shapley_algorithm

I thought about this for quite a while, and I don't think **correlate** maps perfectly onto the stable matching problem.  **correlate**solves a problem that is:

1. simpler, and
1. different.

I think it *could* use Gail-Shapley, but that wouldn't be guaranteed to produce optimal results... and it's more expensive than my "greedy" algorithm.

In all the following examples, `A`, `B`, and `C` are values in `dataset_a` (aka "men") and X, Y, and Z are values in `dataset_b` (aka "women").
The expression `A: XY` means "`A` prefers `X` to `Y`". The expression `A:X=1.5` means "when matching `A` and `X`, their score is `1.5`".

*How is it simpler?*

The stable matching problem only requires a local ordering, where the preferences of any value in either dataset are disjoint
from the orderings of any other value.  But **correlate** uses a "score"--a number--to compute these preferences, and this
score is symmetric; if `A:X=1.5`, then `X:A=1.5` too.

On this related Wikipedia page:

https://en.wikipedia.org/wiki/Lattice_of_stable_matchings

we find a classic example of a tricky stable matching problem:

    A: YXZ
    B: ZYX
    C: XZY

    X: BAC
    Y: CBA
    Z: ACB

Gail-Shapley handles this situation with aplomb.  Does **correlate**?  The answer is... this arrangement of constraints
just can't *happen* with **correlate**, because it uses scores to establish its preferences, and the scores are symmetric.
There are nine possible pairings with those six values. It's impossible to assign a unique score to each of those nine
pairings such that the preferences of each value match those constraints.

(I know--I tried. I wrote a brute-force program that tried every combination. 362,880 attempts later, I declared failure.)

*How is it different?*

Gail-Shapley requires that every value in each dataset expresses a strictly ordered preference for every value in the
other dataset. But in **correlate**, two matches can have the same score.

Consider this expression of a **correlate** problem:

    A:X=100
    A:Y=1

    B:X=100
    B:Y=2

Gail-Shapley can't solve that problem, because X doesn't prefer A or B--it likes them both equally.
(Happily, **correlate** handles *that* situation with aplomb--see the "match boiler" above.)
If we weaken Gail-Shapley to permit lack-of-preference, my hunch is you could contrive inputs where
it would never complete.

In addition, **correlate** uses a numerical score to weigh the merits of each match, and seeks to
maximize the cumulative score across all matches. Gail-Shapley's goals are comparatively modest--any
match that's stable is fine. There may be many stable matchings; Gail-Shapley considers them all
equally good.  There's no guarantee that, if fed digestible **correlate** datasets, Gail-Shapley
would produce the stable match with the highest score.

(I admit, I wasn't able to come up with an example where Gail-Shapley would view two solutions as
equally desirable, but **correlate** would definitely prefer one over the other. Maybe this last
thing isn't an actual problem.)

## Version History

**0.6**

Big performance boost in "fuzzy boiling"!  Clever sorting of fuzzy matches,
and improvements in the stability (as in "stable sort") of `MatchBoiler`,
allowed using an unmodified boiler to process fuzzy matches.  This allowed
removal of `FuzzyMatchBoiler` and the `MatchBoiler.filter()` callback mechanism.

Minor performance improvement in `MatchBoiler`: when recursing, find the
smallest group of connected matches with the same score,
and only recursively check each of those,
rather than all possibly-connected matches with the same score.

Removed `key_reuse_penalty_factor`.
In the early days of **correlate**, I thought redundant keys were uninteresting.
Initially **correlate** didn't even understand rounds; if you mapped the same
key to the same value twice, it only retained one mapping (the one with the
higher weight).  Later I added rounds, but they didn't seem to add much signal.
So I added `key_reuse_penalty_factor`, so you could turn it down, in case it
was adding more noise than signal.
It wasn't until the realization that `key->value` in round 0 and `key->value`
in round 1 were conceptually *two different keys* that I really understood
how redundant mappings of the same key to the same value should work.  And
once rounds maintained distinct counts of `keys / scores` for the scoring
formula, redundant keys in different rounds became *way* more informative
to the final score.   I now think `key_reuse_penalty_factor` is dumb and worse
than useless and I've removed it.  If you think `key_reuse_penalty_factor` is useful,
please contact me and tell me why!  Or, quietly just pre-multiply it into
your weights.


The cumulative effect: a speedup of up to 30% in fuzzy match boiling,
and up to 5% on YTJD tests using a lot of fuzzy keys.  Match boiling got
slightly faster too.

**0.5.1**

Bugfix release.  In the original version, if a match didn't have any matches between
fuzzy keys (with a positive score), it ignored the weights of its exact keys and just
used the raw exact score.

**0.5**

Initial public release.