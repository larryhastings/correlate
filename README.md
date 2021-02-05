# correlate

## A clever brute-force correlator for kinda-messy data

##### Copyright 2019-2020 by Larry Hastings


## Overview

Let's say you've downloaded a bunch of video files that represent
a season of a (presumably public domain!) TV show.  But the filenames
are terrible.  And let's say you have some very clean data from
Wikipedia with the correct titles for all the episodes.
So the word *"Neurostim"* appears in both places.

If you're as fastidious as I am, you want to rename the video files
so they have nice clean names.  You *could* do it by hand.
But what if there are a lot of episodes?
And what do you do if there's an update of the video files?
Do you want to redo the correlation by hand every time there's an update?

Obviously you'd like to automate this.  You want
to match up each filename with its equivalent listing from Wikipedia. The
thing is, it's real-world data--and it's probably a little messy.
Perhaps they aren't in the exact same order.  And while some matches are
obvious, others are less so.  Maybe some episodes are missing in your
directory, or maybe Wikipedia's list is incomplete.

How can you *automate* this process?

**correlate** solves this problem for you.  It correlates values between
two messy but strongly-related datasets.

How it works: you submit your two datasets to
**correlate**, showing it each value, and mining the data and metadata for
"keys" that map to that value.  You then set **correlate** to work.
It thinks for a while, then produces its best guess as to how to match
the two sets.  And its best guess is... hey, that's pretty good!

In essense, **correlate** uses the uniqueness of keys as clues to find
its matches.  If there's a key present in both datasets, but it only maps
to one value in each dataset, odds are good that those two values
should be matched together.

That's the basics.  **correlate** also supports some advanced features:

* A key mapping can optionally specify a *weight*.
* You can map a key *multiple times.*
* Keys can be *fuzzy keys,* keys that may only partially match each other.
* The order of values can inform the matches.  **correlate** calls this *ranking.*

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
        print(f"{match.score:1.3f} {match.value_a:>5} -> {match.value_b}")

produces this output:

    5.750  greg -> Greg
    3.800 steve -> Steve
    1.286 carol -> Carol
    1.222  tony -> Tony


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
We have two options to match those four values:

    A1->B1 and A2->B2
    or
    A1->B2 and A2->B1

But the key `"egyptian"` already helped us choose *A1* and *B1* as
a good match.  Since we already know those are a match, that
eliminates the second option.  Our only choice now is to match
to *A2* -> *B2*.  Choosing a good match based on `"egyptian"` helped
us to eliminated choices and make a good choice for `"nickel"`, too.

In short, **correlate** capitalizes on the *relative uniqueness*
of keys.


## Getting Started With correlate

### Requirements

**correlate** requires Python 3.6 or newer.  It has no
other dependencies.

If you want to run the **correlate** test suite,
you'll need to install the `rapidfuzz` package.
(`rapidfuzz` is a fuzzy string matching library.
It's a lot like `fuzzywuzzy`, except `rapidfuzz`
is MIT licensed, wheras `fuzzywuzzy` is GPL
licensed.)


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
Python data types can be used as keys; they just need to
be hashable.

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
**correlator** thinks this `value_a` maps to this `value_b`.
The `score` is a sort of mathematical confidence level--it's
a direct result of the keys and other metadata you provide
to **correlate**.  The list of matches is sorted by
`score`--higher scores first, as higher scores represent
higher confidence in the match.

That's the basics.  But **correlate** supports some very sophisticated
behavior:

* When mapping a key to a value, you may specify an optional *weight*,
  which represents the relative importance of this key.  The default
  weight is 1.  Higher scores indicate a higher significance; a weight of
  2 tells **correlate** that this key mapped to this value is twice as
  significant.  (Weight is an attribute of a particular mapping of a key
  to a value--an "edge" in the graph of mapping keys to values.)
* A key can map to a value multiple times.  Each mapping can have its own weight.
* If both datasets are ordered, this ordering can optionally influence the match scores.
  **correlate** calls this *ranking.*  Ranking is an attribute of values, not keys.
* Keys can be "fuzzy", meaning two keys can be a partial match rather than a binary yes/no.
  Fuzzy keys in **correlate** must inherit from a custom abstract base class called
  `correlate.FuzzyKey`.

## Sample Code And infer_mv

**correlate** ships with some sample code for your reading pleasure.
The hope is it'll help you get a feel for what it's like to use **correlate**.
Take a look at the scripts in the `tests` and `utilities` directories.

In particular, `utilities` contains a script called `infer_mv`.
`infer_mv` takes a source directory and a list of files and directories
to rename, and produces a mapping from the former to the latter.
In other words, when you run it, you're saying
*"here's a source directory and a list of files and directories to rename.
For each file in the list of things to rename, find the
filename in the source directory that most closely resembles that file,
and rename the file so it's exactly like that other filename from the
source directory."*  (If you ask `infer_mv` to rename a directory,
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

I use `infer_mv` like so:

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
keys must be *hashable.*  This in turn requires that keys
must be *immutable.*

#### Exact Keys

An "exact" key is what **correlate** calls any key that isn't a "fuzzy" key.
Strings, integers, floats, complex, `datetime` objects--they're all fine to use
as **correlate** keys, and instances of many more types too.

When considering matches, exact keys are binary--either they're an exact match
or they don't match at all.  To work with non-exact matches you'll have
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
function should return a number (either `int` or `float`) between (and including)
`0` and `1`, indicating how close a match `self` is to `other`.  If `compare`
returns `1`, it's saying this is a perfect match, that the two values are identical;
if it returns `0`, it's a perfect mismatch, telling **correlate** that the two keys
have nothing in common.

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
assign the comparison a fuzzy score of `1`.  (Currently if this situation
arose it *would* call `a.compare(a)`, but that wasn't true at various
times during development.)

Finally, it's important to note that fuzzy keys are dramatically slower
than exact keys.  If you can express your problem purely using exact keys,
you should do so!  It'll run faster as a result.  You can get a sense of
the speed difference by running `tests/ytjd.test.py` with verbose mode
on (`-v`). A test using the same corpus but switching everything to fuzzy
keys runs about *12x slower* on my computer.


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
            reuse_a=False,
            reuse_b=False)`

> Correlates the two datasets.  Returns a `correlate.CorrelatorResult` object.
>
> `minimum_score` is the minimum permissible score for a match.  It must be
> greater than or equal to 0.
>
> `score_ratio_bonus` specifies the weight of a bonus awarded to a match, based on the ratio of
> the actual score computed between these two values divided by the maximum possible score.
> For more information, consult the [*Score Ratio Bonus*](#score-ratio-bonus) section.
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
> For more information on all these ranking-related parameters,
> consult the [*Ranking*](#ranking-1) section of this document.
>
> `reuse_a` permits values in `dataset_a` to be matched to more than one value in `dataset_b`.
> `reuse_b` is the same but for values in `dataset_b` matching `dataset_a`.
> If you set both reuse flags to True, the `correlate.CorrelatorResult.matches`
> list returned will contain *every* possible match.

`Correlator.print_datasets()`

> Prints both datasets in a human-readable form.  Uses `self.print` to print,
> which defaults to `print`.

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

`CorrelatorResult()`

> The class for objects returned by `Correlator.correlate()`.
> Contains four members:
>
> * `matches`, a `list` of `CorrelatorMatch()` objects, sorted with highest score first
> * `unmatched_a`, the `set` of values from `dataset_a` that were not matched
> * `unmatched_b`, the `set` of values from `dataset_b` that were not matched
> * `statistics`, a `dict` containing human-readable statistics about the correlation

`CorrelatorResult.normalize(high=None, low=None)`

> Normalizes the scores in `matches`.
> When `normalize()` is called with its default values, it adjusts every score
> so that they fall in the range `(0, 1]`.
> If `high` is not specified, it defaults to the highest score in `matches`.
> If `low` is not specified, it defaults to the `minimum_score` used for the correlation.


`CorrelatorMatch()`

> The class for objects representing an individual match made
> by `Correlator.correlate()`.
> Contains three members:
>
> * `value_a`, a value from `dataset_a`.
> * `value_b`, a value from `dataset_b`.
> * `score`, a number representing the confidence in this match.
>   The higher the `score`, the higher the confidence.
>   Scores don't have a predefined intrinsic meaning; they're a result
>   of all the inputs to **correlate.**

`Correlator.str_to_keys(s)`

> A convenience function.
> Converts string `s` into a list of string keys using a reasonable approach.
> Lowercases the string, converts some common punctuation into spaces, then splits
> the string at whitespace boundaries.  Returns a list of strings.


### Getting Good Results Out Of Correlate

Unfortunately, you can't always expect perfect results with **correlate**
every time.  You'll usually have to play with it at least a little.
At its heart, **correlate** is a heuristic, not an exact technology.
It often requires a bit of tuning before it produces the results you want.

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

Ranking can also speed up **correlate** quite a bit.  If there are a
lot of matches that end up with the same score, this can create a lot
of work for the "match boiler" (see below), and that can get expensive
quick.  Even a gentle nudge from ranking information can help differentiate
scores enough to result in a *dramatic* speedup.

#### Minimum Score

Once you've plugged in all your data, you should run the correlation,
print out the result in sorted order with the best
matches on top, then scroll to the bottom and see what the *worst*
5% or 10% of matches look like.

If literally all your matches are already perfect--congratulations!
You're *already* getting good results out of **correlate** and you
can stop reading here.  But if you're not that lucky, you've got more
work to do.

The first step in cleaning up **correlate's** output is usually
to stop it from making bad matches by setting a `minimum_score`.

When you have bad matches, it's usually because the two datasets don't map
perfectly to each other.  If there's a value in `dataset_a` that has no good
match in `dataset_b`, well, **correlate** doesn't really have a way of
knowing that.   So it may match that value to something anyway.

Look at it this way: the goal of **correlate** is to find matches between
the two datasets.  If it's made all the good matches it can, and there's
only one item left in each of the the two datasets, and they have *anything*
in common at all, **correlate** will match those two values together
out of sheer desparation.

However!  Bad matches like these tend to have a very low score.
So all those low-scoring bad matches clump together at the very
bottom.  There'll probably be an inflection point where the scores
drop off significantly and the matches go from good to bad.

This is what `minimum_score` is for.  `minimum_score` tells **correlate**
the minimum permissible score for a match.  When you have a clump of bad
matches at the bottom, you simply set `minimum_score` to be somewhere
between the highest bad match and the lowest good match--and
behold!  No more bad matches!  The values that were used in the bad
matches will move to `unused_a` and `unused_b`, which is almost
certainly the correct place for them.

(Technically, **minimum_score** isn't *actually* the minimum score.
It's ever-so-slightly *less* than the lowest
permitted score.  As in, for a match to be considered viable, its score
must be *greater than* **minimum_score.**  In Python 3.9+, you can
express this concept as:

    actual_minimum_score = math.nextafter(minimum.score, math.inf)

The default value for
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
advice on what to do here.  All I can suggest is to start experimenting.  Change
your keys, adjust your weights, run the correlation again and see what happens.
Usually when I do this, I realize something I can do to improve the data I feed
in to **correlate**, and I can fix the problem externally.)

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

But using weights can be a dual-edged sword.  If your data has mistakes
in it, heavily weighting the bad data can magnify those mistakes.  One bad
heavily-weighted key on the wrong value can inflate the score of a bad match
over the correct match.  And that can result in a vicious cycle--if value
*A1* should match value *B1*, but it get mapped to value *B43* instead,
that means *B1* is probably going to get mismatched too.  Which deprives
another value of its correct match.  And so on and so on and so on.

One final note on weights.  The weight of a key doesn't affect how
*desirable* it is in a match, it only affects the resulting score of that
match.  Consider this scenario involving weighted fuzzy keys:

    FA1 and FA2 are fuzzy keys in dataset_a
    FB is a fuzzy key in dataset_b
    VA1 and VA2 are values in dataset_a

    dataset_a.set(FA1, VA1, weight=1)
    dataset_a.set(FA2, VA2, weight=5)

    FA1.compare(FB) == 0.4
    FA2.compare(FB) == 0.2

If **correlate** had to choose between these two matches, which one
will it prefer?  It'll prefer *FA1*->*FB*, because **correlate**
doesn't consider weights when considering matches.  It always prefers
the match with the higher *unweighted* score.  It's true,
matching *FA2* to *FB* results in a higher final score once you
factor in the weights.  But that doesn't make it a better match.

The best way to conceptualize this: weights don't make matches
*higher quality,* they just make matches more *interesting*
when true.


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

Note that **correlate** is now *very* efficient when it comes to
matching with exact keys.  For most people, the additional runtime cost
for redundant or common keys is probably negligible, and not worth the
additional development time or engoing support cost to make it even worth
considering.  It's true they provide only a tiny amount of signal--but they
also have relatively little runtime cost, either in memory or CPU time.
At this point it's *probably* not worth the bother to almost anybody.

(But here's a theoretical best of both worlds to consider: for very
common keys, consider throwing away the *first* instance.  I admit I
haven't tried this experiment myself.)

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
to, with a debugger or with `Correlator.print_datasets()`.  Making sure you gave
**correlate** the right data can make it not only much more accurate,
it might make it faster too!

#### Normalize Strings

When using strings as keys from real-world sources, I recommend you
*normalize* the strings:
lowercase the strings,
remove most or all punctuation,
and
break the strings up into individual keys at word boundaries.
In the real world, punctuation
and capitalization can both be inconsistent, so throwing it away can help
dispel those sorts of inconsistencies.  **correlate**
provides a utility function called `correlate.str_to_keys()` that does this
for you.  But you can use any approach to string normalizing you like.

You might also consider *interning* your strings.  In my limited experimentation
this provided a small but measurable speedup.

#### Sharpen Your Fuzzy Keys

If you're using fuzzy keys, make sure you *sharpen* your fuzzy keys.
Fuzzy string-matching libraries have a naughty habit of scoring
not-very-similar strings as not *that* much less than almost-exactly-the-same
strings.  If you give that data unaltered to **correlate,** that "everything
looks roughly the same" outlook will be reflected in your results as
mediocre matches.

In general, you want to force your fuzzy matches to extremes.
Two good techniques:

* Specify a minimum score for fuzzy matches, and replace any fuzzy score
  below that minimum with `0`.
  * Possibly remap the remaining range to the entire range.
    For example, if your minimum score is `0.6`, should you simply
    return values from `0.6` to `1`?  Or should you stretch the scores
    over the entire range with `(fuzzy_score - 0.6) / (1 - 0.6)`?
    You may need to experiment with both to find out what works well for you.
* Multiply your fuzzy score by itself.  Squaring or even cubing a fuzzy
  score will preserve high scores and attenuate low scores.
  However, note that the scoring algorithm for fuzzy key matches already
  *cubes* the fuzzy score.  Additional multiplying of the score by itself is
  probably unnecessary in most cases.


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


## Implementation Notes On The Algorithm And The Code

> If the implementation is hard to explain, it's a bad idea.
> --*The Zen Of Python* by Tim Peters

What follows is an exhaustive (and exhausting!) chapter
on the implementation of **correlate**.  This is here
partially for posterity, partially because I like
reading this sort of thing in other people's projects,
but mostly to make it easier to reaquaint myself with
the code when I have to fix a bug three years from now.

### The High-Level Overview

At the heart of **correlate** is a brute-force algorithm.  It's what
computer scientists would call an *O*(n²) algorithm.

**correlate** computes every possible "match"--every mapping of a value in
`dataset_a` to a value in `dataset_b` where the two values have keys in common.
For exact keys, it uses set intersections to ignore pairs of values that have
nothing in common, discarding early matches it knows will have a score of 0.
Sadly, it can't do that for fuzzy keys, which is why fuzzy keys tend to
noticably slow down  **correlate**.

For each key that matches between the two values, **correlate**
computes a score.  It then adds all those scores together,
computing the final cumulative score for the "match",
which it may modifiy based on the various bonuses and factors.
It then iterates over these scores in sorted order, highest score first.
For every match where neither of the two values have been used
in a match yet, it counts that as a "match" and adds it to the output.
(This assumes `reuse_a` and `reuse_b` are both `False`.  Also, this
is a little bit of an oversimplification; see the [*Match Boiler*](#choosing-which-matches-to-keep-the-greedy-algorithm-and-the-match-boiler)
section below.)

One important detail: **correlate** strives to be 100%
deterministic.  Randomness can creep in around the edges in Python
programs; for example, if you ever iterate over a dictionary,
the order you will see the keys will vary from run to run.
**correlate** eliminates every source of randomness it can.
As far as I can tell: given the exact same inputs, it performs
the same operations in the same order and produces the same result,
every time.

There are a number of concepts involved with how the **correlate**
algorithm works, each of which I'll explain in exhausting detail
in the following sub-sections.


### **correlate's** Six Passes And Big-O Complexity

A single **correlate** correlation makes six passes over its data.
Here's a high-level overview of those passes, followed by
deep-dives into the new terms and technical details of those passes.

**Pass 1**

> Iterate over both datasets and compute the "streamlined"
> data.
>
> *Complexity:* *O*(n)


**Pass 2**

> Iterate over all keys and compute a sorted list of all matches
> that could possibly have a nonzero score.  (The list represents
> a match with a pair of indices into the lists of values for each
> dataset.)  This pass also performs all fuzzy key comparisons and
> caches their results.
>
> *Complexity:* *O*(n²), for the fuzzy key comparisons step.
> For a *correlate* run with a lot of fuzzy keys, this is often
> the slowest part of the run.  If your correlate is mostly
> exact keys, this part will be pretty quick, because all the
> *O*(n²) work is done in C code (set intersections, and sorting).

**Pass 3**

> For every match with a nonzero score,
> compute subtotals for matching all fuzzy keys.
> We need to add some of these together to compute the final
> scores for fuzzy key matches.
>
> *Complexity:* *O*(n²)

**Pass 4**

> For every match with a nonzero score:
>
> * compute the scores for matching all exact keys,
> * finalize the scores for fuzzy key match scores,
> * compute the bonuses (score_ratio_bonus, ranking),
> * and store the result per-ranking.
>
> The score for each match is now finalized.
>
> *Complexity:* *O*(n²)

**Pass 5**

> For every ranking approach being used,
> compute the final list of successful matches,
> using the "match boiler" and "greedy algorithm".
>
> *Complexity:* *O*(n log n) (approximate)

**Pass 6**

> Choose the highest-scoring ranking approach,
> compute unseen_a and unseen_b,
> and back-substitute the "indexes" with their actual values
> before returning.
>
> *Complexity:* *O*(n)

Thus the big-O notation for **correlate** overall is *O*(n²).
The slowest part of **correlate** is processing lots of fuzzy
keys; if you can stick mostly to exact keys, your **correlate**
runs will be a lot quicker.

You can see how long **correlate** spent in each of these
passes by examining the `statistic` member of the `CorrelatorResult`
object.  This is a dict mapping string descriptions of
passes to a floating-point number of seconds.  Pass 2's
sub-passes dealing with exact keys and fuzzy keys are
broken out separately, as is the "match boiler" phase
of Pass 5.


### Rounds

If you call **correlate** as follows:

    c = correlate.Correlator()
    o = object()
    c.dataset_a.set('a', o)
    c.dataset_a.set('a', o)

then key `'a'` really *is* mapped to value `o` twice,
and those two mappings can have different weights.
Technically, the correct way to think of this is as
having two edges from the same key to the same value
in the dataset graph.
Another way to think of it is to consider repeated keys as
being two different keys--identical, but somehow distinct.

(If it helps, you can also think of it as being
like two files with the same filename in two different
directories.  They have the same *filename,* but
they're not the same *file.*)


**correlate** calls groups of these multiple mappings *"rounds"*.
A "round" contains all the keys from the Nth time they were
repeated.  Round 0 contains every key, round 1 contains the second
instances of all the keys that were repeated twice, round 2 contains
all the third instances of all the keys that were repeated three times,
etc.
Rounds are per-value, and there are as
many rounds as the maximum number of redundant mappings of
any single key to any particular value in a dataset.

Naturally, exact keys and fuzzy keys use a different method
to determine whether or not something is "the same key".
Technically both types of keys use `==` to determine equivalence.
However, fuzzy keys don't implement a custom `__eq__`, so Python
uses its default mechanism to determine equivalence, which is
really just the `is` operator.  Therefore: exact keys are the
same if `==` says they're the same, and (in practice) fuzzy keys
are the same if and only if they're the same object.

(Of course, you could implement your own `__eq__` when you write
your own fuzzy subclasses.  But I don't know why you would bother.)

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

Again, conceptually, the `"a"` in round 0 is a different key
from the `"a"` in round 1, and so on.

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
be a subset of the keys in round **N**.  (Though not necessarily
a *strict* subset.)

What about weights?  Higher weights are sorted to lower rounds.
The weight for a key *k* in round **N-1** *must* be greater than
or equal to the weight of *k* in round **N**.
In the above example, the `'a'` in round 0 has weight 5, in round 1
it has weight 3, and in round 2 it has weight 1.
(It doesn't matter what order you insert them in, **correlate**
automatically sorts the weights as you add the redundant mappings.)

Thus, round 0 always contains every exact key mapped to
a particular value, with the highest weights for each of those
mappings.

Rounds can definitely help find the best matches.  If the
key `"The"` maps to most of your values once,
that's not particularly interesting, and it won't affect the scores
very much one way or another.  But if there's only one
value in each dataset that `"The"` maps to *twice,*
that's a very strong signal indeed!  **correlate** does an
*excellent* job of noticing unique-ness like that and factoring
it into the scoring.

### Streamlined Data

The **correlate** datasets store data in a format designed
to eliminate redundancy and be easy to modify.  But this representation
is inconvenient for performing the actual correlate.  Therefore, the first
step ("Pass 1") is to reprocess the data into a "streamlined" format.
This is an internal-only implementation detail, and in fact the data
is thrown away at the end of each correlation.  As an end-user you'll
never have to deal with it.  It's only documented here just in case you
ever need to understand the implementation of **correlate**.

This streamlined data representation is an important optimization.
It greatly speeds up computing a match between two values.  And it
only costs a little overhead, compared to all that matching work.
Consider: if you have 600 values in `dataset_a` and 600 values in
`dataset_b`, **correlate** will recompute 1,200 streamlined datasets.
But it'll then use it in as many as 360,000 comparisons!   Spending
a little time precomputing the data in a convenient format saves a
lot of time in the long run.

The format of the streamlined data changes as the implementation
changes.  And since it's an internal-only detail, it's largely undocumented
here.  If you need more information, you'll just have to read the code.
Search the code for the word `streamlined`.


### The Scoring Formula, And Conservation Of Score

For each match it considers, **correlate** computes the intersection of
the keys that map to each of those two values in the two datasets,
then computes a score based on each of those key matches.
This scoring formula is the heart of **correlate**, and it was a key
insight--without it **correlate** wouldn't work nearly as well as it does.

In the abstract, it looks like this:

    for value_a in dataset_a:
        for value_b in dataset_b:
            subtotal_score = 0
            for key_a, weight_a that maps to value_a:
                for key_b, weight_b that maps to value_b:
                    score = value of key_a compared to key_b
                    cumulative_a = the sum of all scores resulting from key_a mapping to any value in dataset_b
                    cumulative_b = the sum of all scores resulting from key_b mapping to any value in dataset_a
                    score_ratio_a = score / cumulative_a
                    score_ratio_b = score / cumulative_b
                    unweighted_score = score * score_ratio_a * score_ratio_b
                    score_a = weight_a * unweighted_score_a
                    score_b = weight_b * unweighted_score_b
                    final_score = score_a * score_b
                    subtotal_score += final_score

Two notes before we continue:

* `key_a` and `key_b` must always be *per-round,* for a number
of reasons, the least of which is because we use their
weights in computing the `final_score`.

* `subtotal_score` is possibly further adjusted by `score_ratio_bonus`
and ranking, if used.  We'll discuss that later.

This formula is how **correlate** computes a mathematical representation
of "uniqueness".  The fewer values a key maps to in a dataset,
the higher it scores.  A key that's only mapped once in each
dataset scores 4x higher than a key mapped twice in each dataset.

This scoring formula has a virtuous-feeling mathematical
property I call *"conservation of score".*  Each key that
you add to a round in a dataset adds 1 to the total cumulative
score of all possible matches; when you map a key to multiple
values, you divide this score up evenly between those values.
For example, if the key `x` is mapped to three values in `dataset_a`
and four values in `dataset_b`, each of those possible matches
only gets 1/12 of that key's score, and the final cumulative
score for all matches only goes up by 1/12.  So a key always
adds 1 to the sum of all scores across all *possible* matches,
but only increases the actual final score by the amount of
signal it *actually* communicates.

Also, now you see why repeated keys can be so interesting.
They add 1 for *each round* they're in, but that score is only
divided by the number of values they're mapped to *in that round!*
Since there tend to be fewer and fewer uses of a key in
subsequent rounds, the few keys that make it to later rounds
can potentially score much higher than they did in earlier
rounds, making them a more noteworthy signal.


### Matching And Scoring Exact Keys

The "streamlined" data format for exact keys looks like this:

    exact_rounds[index][round] = (set(d), d)

That is, it's indexed by "index" (which represents the value), then
by round number.  That gives you a tuple containing a dict mapping
keys to weights, and a `set()` of just the keys.
**correlate** uses `set.intersection()` (which is super fast!)
to find the set of exact keys the two values have in common for that round.
The `len()` of this resulting set is the base cumulative score for that round,
although that number is only directly useful in computing `score_ratio_bonus`.

Although **correlate** uses the same scoring formula for both exact keys and
fuzzy keys in an abstract sense, scoring matches between exact keys is much
simpler in practice.  Let's tailor the "abstract" scoring algorithm above for
exact keys.  This lets us optimize the algorithm in a couple places, making
it much faster!

First, with exact keys, naturally they're either an exact match or they aren't.
If they're an exact match, they're the same Python value.  Therefore `key_a` and
`key_b` must be identical.  Therefore, conceptually, we can swap them.  Let's
rewrite the "scoring formula" equation slightly:

    cumulative_a = the sum of all scores between key_b and all keys in dataset_b
    cumulative_b = the sum of all scores between key_a and all keys in dataset_a

All we've changed is: we've swapped `key_a` and `key_b`.
(Why?  It'll help.  Hey, keep reading.)

Now consider: `score` for exact keys is always either `1` or `0`.  It's `1` when
two keys are exactly the same, and `0` otherwise.  If the base `score` for the
match is `0`, then the `final_score` will be `0` and we can skip all of it.
So we only ever compute a `final_score` when `score` is `1`, when the keys
are identical.

Since `score` is only ever used as a multiplier, we can discard it.

`cumulative_a` and `cumulative_b` are similarly easy to compute.
They're just the number of times that key is mapped to any value in
the relevant dataset, *in that round.*  These counts are precomputed
and stored in the "streamlined" data.

So, finally: if you do the substitutions, and drop out the constant `score`
factors, `final_score` for exact keys is computed like this:

    final_score = (weight_a * weight_b) / (cumulative_a * cumulative_b)

Which we can rearrange into:

    final_score = (weight_a / cumulative_b) * (weight_b / cumulative_a)

At the point we precompute the streamlined data for `dataset_a`,
we know `weight_a`, and we can compute `cumulative_b` because it only
uses terms in `dataset_a`.  So we can pre-compute those terms,
making the final math:

    # when computing the streamlined data
    precomputed_a = weight_a / cumulative_b
    precomputed_b = weight_b / cumulative_a

    # ...

    # when computing the score for a matching exact key
    final_score = precomputed_a * precomputed_b

That's a *lot* simpler!  And these optimizations made **correlate** a *lot* faster.


### Fuzzy Keys

Let me tell you a wonderful bed-time story.
Once upon a time, **correlate** was small and beautiful.
But that version only supported exact keys.
By the time fuzzy keys were completely implemented, and feature-complete,
and working great, **correlate** was much more complex and... "practical".
It's because fuzzy keys introduce a lot of complex behavior, resulting in
tricky scenarios that just don't arise with exact keys.

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
>    * In `dataset_a`, the key `AnimalKey("Horse")` maps to Farm X *twice.*
>
>    * In `dataset_b`, the keys `AnimalKey("Horse/Clydesdale")`
>    and `AnimalKey("Horse/Shetland Pony")` map to Farm X.

Question: should one of the `"Horse"` keys in `dataset_a` match
`"Horse/Clydesdale"` in `dataset_b`, and should the other `"Horse"`
key match `"Horse/Shetland Pony"`?

Of course they should!  But consider the ramifications: we just matched
a key from *round 2* in `dataset_a` to a key from *round 1* in `dataset_b`.
That's simply *impossible* with exact keys!

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
**correlate** will consider *FA1* -> *FB* and also *FA2* -> *FB*
and only keep the match with the highest score.  A match "consumes"
the two keys (one from each dataset) and they can't be matched again.
(Again: when I say "key" here, I mean "this key in this round".)
The flip side of this: a key that isn't matched *isn't* "consumed".
What do we do with it?  The example above with horses and farms makes
it clear: unconsumed fuzzy keys should get recycled--reused in
subsequent rounds.

So, where exact keys use very precise "rounds", fuzzy keys
require a more dynamic approach.  Precisely speaking, an unused key in
round *N* conceptually "survives" to round *N+1*.  That's what the above
example with farms and ponies shows us; in round 0, if `"Horse/Clysedale"`
in `dataset_a` gets matched to `"Horse"` in `dataset_b`,
`"Horse/Shetland Pony"` in `dataset_a` goes unmatched, and survives,
and advances on to round 1.  This also made scoring more complicated.
(For more on this, check out the test suite.  There's a regression test
that exercises this exact behavior.)

After a bunch of rewrites, I found the fastest way to compute fuzzy matches
was: for each fuzzy type the two values have in common, compute *all possible
matches* between all fuzzy keys mapping to the two values, even mixing
between rounds.  Then sort the matches, preferring higher scores to lower
scores, and preferring matches in lower rounds to matches in higher rounds.

The streamlined data for fuzzy keys looks like this:

    fuzzy_types[index][type] = [
                               [(key1, weight, round#0),  (key1, weight, round#1), ...],
                               [(key2, weight, round#0),  (key2, weight, round#1), ...],
                               ]


That is, they're indexed by index (a representation of the value),
then by fuzzy type.  That gets you a list of lists.  Each inner list
is a list of tuples of

    (key, weight, round_number)

where `key` is always the same in all entries in the list, and
`round_number` is always the same as that tuple's index in that list.

When computing matches between fuzzy keys, **correlate** takes the
two lists of lists and does nested `for` loops over them.  Since the
keys don't change, it only needs to look up the fuzzy score once.
If the fuzzy score is greater than 0, it stores the match in an
array.

Once it's done with the fuzzy key matching, it sorts this array of matches,
then use the "match boiler" to reduce it down so that every per-round key
is matched at most once.  (The "match boiler" is discussed later; for now
just assume it's a magic function that does the right thing.  Though I had
to ensure it was super-stable for this approach to work.)

Sorting these fuzzy key matches was tricky.  They aren't merely sorted
by score; we also must ensure that fuzzy key matches from earlier rounds
are *always* consumed before matches using that key in later rounds.
So we use a special `sort_by` tuple as the sorting key, computed as follows:

    key_a, weight_a, round_a = fuzzy_types_a[index_a][type]...
    key_b, weight_b, round_b = fuzzy_types_b[index_b][type]...
    fuzzy_score = key_a.compare(key_b)
    lowest_round_number  = min(round_a, round_b)
    highest_round_number = max(round_a, round_b)
    sort_by = (fuzzy_score, -lowest_round_number, -highest_round_number)

The `-lowest_round_number` trick is the very clever bit.  This lets
us sort with highest values last, which is what the "match boiler" wants.
But negating it means lower round numbers are now *higher* numbers, which
lets us prefer keys with *lower* round numbers.

In terms of the abstract scoring formula, `score` is the fuzzy score,
what's returned by calling the `compare()` method. And `cumulative_a`
is the sum of all fuzzy `score` scores for all matches using `key_a`.


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
matched between `X` and `Y` than matched between `X` and `Z`.
That small nudge is generally all that's needed to let **correlate**
disambiguate these situations and pick the correct match.

Two things to note.  First, when I say "keys", this is another situation
where the same key mapped twice to the same value is conceptually considered
to be two different keys.
In the example I gave in the **Rounds** subsection above, where `value_a` is `o`
and `value_b` is `o2`, `possible_a` would be 6 and `possible_b` would be 4.

Second, the scores used to compute `actual` and `possible` are *unweighted.*
If a match between two fuzzy keys resulted in a fuzzy score of `0.3`,
that adds `0.3` to both `actual_a` and `actual_b`, but each of those fuzzy
keys adds `1.0` to `possible_a` and `possible_b` respectively.
Weights are always ignored when computing `score_ratio_bonus`, just like
they're ignored when comparing matches.


### Choosing Which Matches To Keep: The "Greedy Algorithm" And The "Match Boiler"

Here's a problem, presented in the abstract: if you're presented with
a list of match objects called `matches`,
where each match object `M` has three attributes `value_a`, `value_b`,
and `score`, how would you compute an optimal subset of `matches`
such that:

* every discrete value of `value_a` and `value_b` appears only once, and
* the sum of the `score` attributes is maximized?

Finding the perfectly optimal solution would require computing every
possible set of matches, then computing the cumulative score of that
set, then choosing the set with the highest score.  Unfortuantely,
that algorithm is *O*(nⁿ),
which is so amazingly expensive that we can't even consider it.
(You probably want your results from **correlate** before our sun
turns into a red giant.)

Instead, **correlate** uses a comparatively cheap "greedy" algorithm
to compute the subset.  It's not *guaranteed* to produce the optimal
subset, but in practice it seems to produce optimal results on
real-world data.

Here's a short description of the **correlate** "greedy" algorithm:

* Sort `matches` with highest score first.
* For every match `M` in `matches`:
    * if `value_a` hasn't been matched yet,
    * and `value_b` hasn't been matched yet,
        * keep `M` as a good match,
        * remember that `value_a` has been matched,
        * and remember that `value_b` has been matched.

The sorting uses Python's built-in sort (Timsort), so it's
*O*(n log n).  It's implemented in C so it's pretty quick.
The `for` loop is *O*(n).

However!  Late in development of **correlate** I
realized there was a corner case where odds are good the
greedy algorithm wouldn't produce an optimal result.
Happily, this had a relatively easy fix, and the
fix didn't make **correlate** any slower in the general case.

Let's start with the problem, the nasty corner case.  What if two
matches in the list are both viable, and they have the *same* score,
and they have either `value_a` or `value_b` in common?
It's ambiguous as to which match the greedy algorithm
will choose.  But choosing the wrong one *could* result
in less-than-optimal scoring in practice.

Here's a specific example:

* `dataset_a` contains fuzzy keys `fka1` and `fka2`.
* `dataset_b` contains fuzzy keys `fkbH` and `fkbL`.
  Any match containing `fkbH` has a higher score than any match containing `fkbL`.
  (the H means *high* scoring,  the L means *low* scoring.)
* The matches`fka1->fkbH` and `fka2->fkbH` have the same score.
* The match `fka1->fkbL` has a lower score than `fka2->fkbL`.

The cumulative score over all matches would be higher if
**correlate** chose `fka2->fkbL` to `fka1->fkbL`.
And since scores in **correlate** are an indicator of
the quality of a match, a higher cumulative score reflects
higher quality matches.  Therefore we should maximize the
cumulative score wherever possible.

But the greedy algorithm can only pick the higher-scoring second
match if it previously picked `fka1->fkbH`.  And there's no guarantee
that it would!  If two items in the list have the same score,
it's ambiguous which one the greedy algorithm would choose.

To handle this properly it needs to look ahead and experiment.
So that's why I wrote what I call the "match boiler", or the
"boiler" for short.  The boiler uses a hybrid approach.  By default,
when the scores for matches are unique, it uses the "greedy"
algorithm.  But if it encounters a group of items with matching
scores, where any of those items have `value_a` or `value_b` in
common, it recursively runs an experiment where it chooses each
of those matches in turn.  It computes the score from each of these
recursive experiments and keeps the one with the highest score.

(If two or more experiments have the same score, it keeps the first one
it encountered with that score--but, since the input to the "match boiler"
is a list, sorted with highest scores to the end, technically it's the
*last* entry in the list that produced the high-scoring experiment.)

With the "match boiler" in place, **correlate** seems to produce optimal
results even in these rare ambigous situations.

I'm honestly not sure what the *big-O* notation is for the "match boiler".
The pathological worst case
is *probably* on the order of *O*(n log n), where the `log n` component
represents the recursions.
In this case, every match has the same score, and they're all connected to
each other via having `value_a` and `value_b` in common.  I still don't
think the "match boiler" would be as bad as *O*(n²).
The thing is, sooner or later the recursive step would cut the
"group" of "connected items" in half (see next section).  It's guaranteed
*not* to recurse on every single item.
So I assert that roughly cuts the number of recursive
steps down to `log n`, in the pathological worst case that you would
never see in real-world data.

#### Cheap Recursion And The "Grouper"

But wait!  It gets even more complicated!

Compared to the rest of the algorithm, the recursive step of the
"match boiler" is quite expensive.  It does reduce the domain of
the problem at every step, so it's guaranteed to complete...
someday.  But, if we're not careful, it'll perform a lot of
expensive and redundant calculations.  So there are a bunch
of optimizations to the match boiler's recursive step, mainly
to do with the group of matches that have the same score.

The first step is to analyze these matches and boil them out
into "connected groups".  A "connected group" is a set of
match objects where either each object has a `value_a` or a
`value_b` in common with another object in the group.  These
are relevant because choosing one of the matches from these
groups will remove at least one other value from consideration
in that group, because that `value_a` or `value_b` is
now "used" and so all remaining match using those values
will be discarded.

An example might help here.  Let's say you have these
six matches in a row all with the same score:

    match[1]: value_a = A1, value_b = B1
    match[2]: value_a = A1, value_b = B2
    match[3]: value_a = A2, value_b = B1
    match[4]: value_a = A3, value_b = B2
    match[5]: value_a = A10, value_b = B10
    match[6]: value_a = A10, value_b = B11

This would split into two "connected groups": matches 1-4
would be in the first group, and matches 5-6 would be in the
second.  Every match in the first group has one member
(`value_a` or `value_b`) in common with at least one other
match in the first group; every match in the second group
has one member in common with at least one other match in
the second group.  So every match in the first group is
"connected"; if you put them in a graph, every match would
be "reachable" from every other match in that group,
even if they aren't directly connected.  For example,
`match[4]` doesn't have any members in common with `match[1]`,
but both of them have a member in common with `match[2]`.
But none of the matches in the first group have any member in
common with any of the matches in the second group (and
naturally vice-versa).

There's a utility function called `grouper()` that computes
these connected groups.  (`grouper()` only handles the case
when `reuse_a == reuse_b == False`; there are alternate
implementations to handle the other possible cases, e.g.
`grouper_reuse_a()`.)

The second step is to take those "connected groups" and,
for every group containing only one match object,
"keep" it immediately.  We already know we're keeping
these and it's cheaper to do that first.

Now that the only remaining connected groups are size 2 or
more, the third step is to recurse over each of the values of the
*smallest* of these connected groups.  Why the smallest?
It's cheaper.  Let's say there are 50 items left in the list
of matches.  At the top are 6 match objects with the same score.
There are two groups: one of length 2, the other of length 4.

The important realization is that, when we perform the experiment
and recurse using each of these values, we're still going to
have to examine all the remaining matches we didn't throw away.
The number of operations we'll perform by looping and recursing is,
roughly, **N** • **M**, where **N** is `len(group)` and **M** is
`len(matches - group)`.  So which one has fewer operations:

* 2 x 48, or
* 4 x 46?

Obviously the first one!  By recursing into the smaller group,
we perform fewer overall operations.

(There's a theoretical opportunity for further optimization here:
when recursing, if there's more than one connected group of length 2
or greater, pass in the list of groups we *didn't*
consume to the recursive step.  That would save the recursive
call from re-calculating the connected groups.  In practice I imagine this
happens rarely, so handling it would result in a couple of `if`
branches that never get taken.  Also, it's a little more complicated
than it seems, because you'd have to re-use the `grouper()` on
the group you're examining before passing it down, because it might
split it into two groups.  In practice it wouldn't speed up anybody's
correlations, and it'd make the code more complicated.  So let's skip it.
The code is already more-or-less correct in these rare circumstances
and that's good enough.)


#### The Match Boiler Reused For Fuzzy Key Scoring

Once my first version of the "match boiler" was done, I realized I could reuse
it for boiling down all fuzzy key matches too.  Fuzzy key matches already
used basically the same "greedy" algorithm that were used for matches,
and it dawned on me that the same corner case existed here too.

My first attempt was quite complicated, as the "match boiler" doesn't
itself understand rounds.  I added a callback which it'd call every time it
kept a match, which passed in the keys that got matched.  Since those keys
were now "consumed", I would inject new matches using those keys from
subsequent rounds (if any). This worked but the code was complicated.

And it got even more complicated later when I added the recursive step!
I had to save and restore all the state of which fuzzy keys had been
consumed from which rounds.  I wound up building it into the subclass
of `MatchBoiler`, which is part of why `MatchBoiler` clones itself
when recursing.  This made the code cleaner but it was still clumsy
and a bit slow.

The subsequent rewrite using the `sort_by` tuple was a big win all around:
it simplified the code, it let me remove the callback, it let the match
boiler implicitly handle all the rounds without really understanding them,
*and* it was even slightly faster!

But this is why it's so important that the boiler is super-stable.
Earlier versions of the match boiler assumed it could sort the
input array any time it wanted.  But the array passed in was sorted
by score, *then* by round numbers--highest score is most important,
lowest round number is second-most important.
And the array is sorted with highest score, then lowest round number, last.
When recursing, the match boiler has to prefer the *last* entry in its
input that produced the same score--otherwise, it might accidentally
consume a key from a later round before consuming that key from an
earlier round.

I didn't want to teach the boiler to understand this `sort_by` tuple.
Happily, I didn't have to.  It wasn't much work to ensure that the boiler
was super-stable, and once that was true it always produced correct results.
(Not to mention... faster!)


#### Theoretical Failings Of The Match Boiler

Even with the "match boiler", you can still contrive scenarios
where **correlate** will produce arguably sub-optimal results.
The boiler only tries experiments where the matches have the
same score.  But it's possible that the greedy algorithm may
find a local maximum that causes it to miss the global maximum.

If `A` and `B` are values in `dataset_a`, and `X` and `Y` are
values in `dataset_b`, and the matches have these scores:

    A->X == 10
    A->Y == 9
    B->X == 8
    B->Y == 1

In this scenario, the boiler will pick `A->X`, which means it's
left with `B->Y`.  Total score: 11.  But if it had picked `A->Y`,
that means it would get to pick `B->X`, and the total score would
be 17!  Amazing!

Is that better?  Your first reaction is probably "of course!".
But in an abstract, hypothetical scenario like this, it's
hard to say for sure.  I mean, yes it's a better *score.*  But
is it a better *match?*  Is this the output the user would have
wanted?  Who knows--this scenario is completely hypothetical in
the first place.

I doubt this is a real problem in practice.  Ensuring **correlate**
handles the ambiguous scenario where items had identical scores is
already "gilding the lily", considering how rare it happens with
real-world data.  And when would real data behave in this contrived
way?  Why would `A` score so highly against `X` and `Y`, but `B` scores
high against `X` but low against `Y`?  If `B` is a good match for `X`,
and `X` is a good match for `A`, and `A` is a good match for `Y`, then,
with real-world data, transitivity would suggest `B` is a good match
for `Y`.  This contrived scenario seems more and more contrived the more
we look at it, and unlikely to occur in the real world.

I think pathological scenarios where the "match boiler" will fail like
this aren't realistic.  And the only way I can think of to fix it is
with the crushingly expensive *O*(nⁿ) algorithm.
It's just not worth it.  So, relax!  As we say in Python: YAGNI.


### Ranking

Ranking information can help a great deal.
If a value in `dataset_a` is near the beginning, and the order
of values is significant, then we should prefer matching it to values
in `dataset_b` near the beginning too.  When the datasets are
ordered, matching the first value in `dataset_a` against the last
value in `dataset_b` is probably a bad match.

Conceptually it works as follows: when scoring a match,
measure the distance between
the two values and let that distance influence the score.  The closer
the two values are to each other, the higher the resulting score.

But how do you compute that distance?  What do the ranking numbers mean?
**correlate** supports two possible interpretations
of the rankings, what we'll call *absolute* and *relative* ranking.
These two approaches differ in how they compare the ranking numbers,
as follows:

* *Absolute* ranking assumes the ranking numbers are the same
  for both datasets.  `ranking=5` in `dataset_a` is a perfect
  match to `ranking=5` in `dataset_b`.  This works well when
  your datasets are both reasonably complete; if they're different
  sizes, perhaps one or both are truncated at either the beginning
  or end.
* *Relative* ranking assumes that the two datasets represent the
  same range of data, and uses the ratio of the ranking of a value
  divided by the highest ranking set in that dataset to compute
  its relative position.  If the highest ranking we saw in a
  particular dataset was `ranking=150`,
  then a value that has `ranking=12` set is calculated to be 8%
  of the way from the beginning to the end.  This percentage
  is calculated similarly for both datasets, and the distance
  between two values is the distance between these two percentages.
  This works well if one or both of your datasets are sparse.

For example, if `dataset_a` had 100 items ranked 1 to 100,
and `dataset_b` had 800 items ranked 1 to 800, a value to
`dataset_a` with `ranking=50` in *absolute* ranking
would be considered closest to a value in `dataset_b` with `ranking=50`,
but when using *relative* ranking
it'd be considered closest to a value in `dataset_b` with `ranking=400`.

Which one does **correlate** use?  It's configurable with the `ranking`
parameter to `correlate()`.  By default it uses the "best" ranking.
"Best" ranking means **correlate** compute a score using *both*
methods and chooses the one with the highest score.
You can override this by supplying a different value to `ranking`
but this shouldn't be necessary.  (Theoretically it should be faster
to use only one ranking approach.  Unfortunately this hasn't been
optimized yet, so using only one ranking doesn't currently speed
things up.)

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
in computing the "f-strings" for the log, but the calls to the logging
functions definitely added overhead too.

My solution: by default, each of the debug print statements
is commented out.
**correlate** ships with a custom script preprocessor called
`debug.py` that can toggle debugging on and off, by uncommenting and
re-commenting the debug code.

How does it know which lines to uncomment?  Each line of the logging-only
code ends with the special marker "`#debug`".

To turn on this logging, run the `debug.py` script in the same directory
as **correlate's** `__init__.py` script.  Each time you run it, it'll
toggle (comment / uncomment) the debug print statements.
Note that the debug feature in **correlate** requires Python 3.8 or higher,
because it frequently uses 3.8's beloved "equals sign inside f-strings" syntax.

By default the logging is sent to stdout.  If you want to override where
it's sent, write your own `print` function, and assign it to your
`Correlator` object before calling `correlate()`.

The format of the log is undocumented and subject to change.  Good luck!
The main thing you'll want to do is figure out the "index" of the values
in `dataset_a` and `dataset_b` that you want to compare, then search for
`" (index_a) x (index_b) "`.  For example, if the match you want to see
is between value index 35 in `dataset_a` and value index 51 in `dataset_b`,
search in the log for `" 35 x 51 "`. (The leading and trailing spaces
means your search will skip over, for example, `235 x 514`.)


### Alternate Fuzzy Scoring Approaches That Didn't Work

I find the math behind fuzzy scoring a bit surprising.
If you boil down the formula to its constituent factors,
you'll notice one of the factors is `fuzzy_score` *cubed.*
Why is it *cubed?*

The simplest answer: that's the first approach that seemed to work
properly.  To really understand why, you'll need to understand the
history of fuzzy scoring in **correlate**--all the approaches
I tried first that *didn't* work.

Initially, the score for a fuzzy match was simply the fuzzy score
multiplied by the weights and other modifiers.
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
In the "YTJD" test, every value had one or more fuzzy keys, depending
on the test: every value always had a fuzzy date key, and depending
on the test it might have a fuzzy title key and/or a fuzzy episode number
key too.  So each of the 812 values in the first dataset had one
fuzzy key for each fuzzy type, and each of the 724 values in the second
dataset did too.  Even if we got a perfect fuzzy match, the maximum score
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
Let's plug those numbers into our formula, shall we!
We get `0.000001 / (0.000001 * 0.000001)`, which is `1000000.0`.
A million!  That's crazy!  We've taken an absolutely
terrible fuzzy match and inflated its score to be nonsensically high.
Clearly that's not right either.

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
    cumulative_a = the cumulative score of all matches between key_a and every fuzzy key of the same type in dataset_b
    cumulative_b = the cumulative score of all matches between key_b and every fuzzy key of the same type in dataset_a
    score_ratio_a = fuzzy_score / cumulative_a
    score_ratio_b = fuzzy_score / cumulative_b
    unweighted_score = fuzzy_score * score_ratio_a * score_ratio_b

The final trick really was realizing what `score_ratio_a` represents.
Really, it represents the ratio of how much *this* fuzzy match for `key_a`
contributed to the sum of *all* fuzzy matches for `key_a`
across all successful matches in `dataset_a`.

### Why correlate Doesn't Use The Gale-Shapley Algorithm

A friend asked me if the problem **correlate** solves is isomorphic to the Stable Matching Problem:

https://en.wikipedia.org/wiki/Stable_matching_problem

Because, if it was, I could use the Gale-Shapley algorithm:

https://en.wikipedia.org/wiki/Gale%E2%80%93Shapley_algorithm

I thought about this for quite a while, and I don't think the problem **correlate**
solves maps perfectly onto the stable matching problem.  **correlate** solves a problem that is:

1. simpler,
2. different, and
3. harder.

For inputs that are valid for both Gale-Shapley and **correlate**, I assert that both
algorithms will return the same results, but **correlate** will be faster.

(Not a claim I make lightly!  Gale and Shapley were both brilliant
mathematicians--they each independently won the *von Neumann* prize!--and the
Gale-Shapley algorithm is marvelous and elegant.  It's just that **correlate**
can take shortcuts Gale-Shapley cannot, because **correlate** is solving
a simpler problem.)

In all the following examples, `A`, `B`, and `C` are values in `dataset_a` and `X`, `Y`, and `Z` are values
in `dataset_b`.  The expression `A: XY` means "`A` prefers `X` to `Y`". The expression `A:X=1.5` means
"when matching `A` and `X`, their score is `1.5`".  When I talk about Gale-Shapley, `dataset_a` will stand for the
"men" and `dataset_b` will stand for the "women", which means `A` is a man and `X` is a woman.  Where we need to talk
about the matches themselves, we'll call them `P` and `Q`.

#### How is it simpler?

The stable matching problem only requires a local ordering, where the preferences of any value in either dataset
are disjoint from the orderings of any other value.  But **correlate** uses an absolute "score"--a number--to compute
these preferences, and this score is symmetric; if `A:X=1.5`, then `X:A=1.5` too.

On this related Wikipedia page:

https://en.wikipedia.org/wiki/Lattice_of_stable_matchings

we find a classic example of a tricky stable matching problem:

    A: YXZ
    B: ZYX
    C: XZY

    X: BAC
    Y: CBA
    Z: ACB

Gale-Shapley handles this situation with aplomb.  Does **correlate**?
The answer is... this arrangement of constraints just can't *happen*
with **correlate**, because it uses scores to establish its preferences,
and the scores are symmetric. There are nine possible pairings with
those six values. It's impossible to assign a unique score to each of
those nine pairings such that the preferences of each value match
those constraints.

(And, yes, I'm pretty certain.  Not only did I work my way through it,
I also wrote a brute-force program that tried every possible combination.
362,880 attempts later, I declared that there was no possible solution.)

#### How is it different?

One minor difference: Gale-Shapley specifies that the two sets be of
equal size; **correlate** permits the two sets to be different sizes.
But extending Gale-Shapley to handle this isn't a big deal.  Simply
extend the algorithm to say that, if the size of the two datasets are
inequal, swap the datasets if necessary so that the "men" are the
larger group. Then, if you have an unmatched "man" who iterates
through all the "women" and nobody traded up to him, he remains
unmatched.

The second thing: Gale-Shapley requires that every value in each
dataset expresses a strictly ordered preference for every value
in the other dataset. But in **correlate**, two matches can have
the same score.

Consider this expression of a **correlate** problem:

    A:X=100
    A:Y=1

    B:X=100
    B:Y=2

Gale-Shapley as originally stated can't solve that problem, because
X doesn't prefer A or B--it likes them both equally.  It wouldn't
be hard to extend Gale-Shapley to handle this; in the case where it
prefers two equally, let it arbitrarily pick one.  For example,
if X prefers A and B equally, say "maybe" to the first one that asks,
and then let that decide for you that you prefer A to B.

#### How is it harder?

Here's the real problem.

**correlate** uses a numerical score to weigh the merits of each match, and seeks to
maximize the cumulative score across *all* matches. Gale-Shapley's goals are comparatively
modest--any match that's stable is fine. There may be multiple stable matchings; Gale-Shapley
considers them all equally good.

In practice, I think if you apply the original Gale-Shapley algorithm to an input data set
where the matches have numerical scores, it *would* return the set of matches with the
highest cumulative score.  In thinking about it I haven't been able to propose a situation
where it wouldn't.  The problem lies in datasets where two matches have the *same* score--which
the original Gale-Shapley algorithm doesn't allow.

Ensuring that **correlate** returns the highest cumulative score in this situation
required adding the sophisticated recursive step to the "match boiler".  We'd have to make
a similar modification to Gale-Shapley, giving it a recursive step.  Gale-Shapley is
already *O*(n²); I think the modified version would be *O*(n² log n).
(But, like **correlate**, this worst-case shouldn't happen with real-world data.)
Anyway, a modified Gale-Shapley that works for all **correlate** inputs is definitely
more expensive than what **correlate** has--or what it needs.

#### Mapping Gale-Shapley To The Correlate Greedy Algorithm

Again, the set of valid inputs for **correlate** and Gale-Shapley aren't
exactly the same.  But there's a lot of overlap.  Both algorithms can
handle an input where:

* we can assign every match between a man `A` and a woman `X` a numerical score,
* every match involving any particular man `A` has a unique score,
* and also for every woman `X`,
* and there are exactly as many men as there are women.

I assert that, for these mutually acceptable inputs, both algorithms
produce the same result.  Here's an informal handwave-y proof.

First, since Gale-Shapley doesn't handle preferring two matches equally,
we'll only consider datasets where all matches have a unique score.
This lets us dispense with the match boiler's "recursive step", so all we
need is the comparatively simple "greedy algorithm".  (Again: this
"greedy algorithm" is much cheaper than Gale-Shapley, but as I'll show,
it's sufficient for the simple problem domain we face here.)

So let's run Gale-Shapley on our dataset.  And every time we perform
an operation, we write it down in a list--we write down
"man `A` asked woman `X`" and whether her reply was *maybe* or *no*.

Observe two things about this list:

* First, order is significant in this list of operations.  If you change
the order in which particular men ask particular women, the pattern of
resulting *maybe* and *no* responses will change.

* Second, the *last* "maybe" said by each woman is always,
effectively, a *yes*.

So let's iterate backwards through this list of matches, and the first
time we see any particular woman reply *maybe*, we change that answer
to a *yes.*

Next: observe that we can swap any two adjacent operations--with one
important caveat.  We must maintain this invariant: for every woman `X`,
for every operation containing `X` that happens after `X` says *yes*,
`X` must say *no.*

Thus, if there are two adjacent operations `P` and `Q`, where `P`
is currently first, and we want to swap them so `Q` is first,
and if the following conditions are all true:

* The same woman `X` is asked in both `P` and `Q`.
* In `Q` the woman `X` says either *maybe* or *yes.*
* In `P` the woman `X` says *maybe.*

Then we can swap `P` and `Q` if and only if we change `X`'s
response in `P` to *no.*

Now that we can reorder all the operations, let's sort the
operations by score, with the highest score first.
Let's call the operation with the highest score `P`,
and say that it matches man `A` with woman `X`.

We now know the following are true:

* `X` is the first choice of `A`.  This must be true because
  `P` is the match with the highest score.  Therefore `A` will
  ask `X` first.
* `A` is the first choice of `X`, again because `P` is the
  match with the highest score.  Therefore `X` is
  guaranteed to say *yes*.

Since the first operation `P` is guaranteed to be a *yes*,
that means that every subsequent operation involving either
`A` or `X` must be a *no*.

We now iterate down the list to find an operation `Q`
involving man `B` and woman `Y`. We define `Q` as the
first operation such that:

* `Q != P`, and therefore `Q` is after `P` in our ordered list of operations,
* `B != A`, and
* `Y != X`.

By definition `Q` must also be a *yes*, because `B` and `Y`
are each other's first choices now that `A` and `X` are
unavailable for matching.  If there are any operations
between `P` and `Q`, these operations involve either `A` or `X`.
Therefore they must be *no*.  Therefore `Q` represents the
highest remaining preference for both `B` and `Y`.

Observe that the whole list looks like this.  Every *yes* is
the first operation for both that man and that woman in which
they weren't paired up with a woman or man (respectively) that
had already said *yes* to someone else.

This list of operations now more or less resembles the operations
performed by the **correlate** "greedy" algorithm. It sorts the
matches by score, then iterates down that sorted list.  For every
man `A` and woman `X`, if neither `A` nor `X` has been matched yet,
it matches `A` and `X` and remembers that they've been matched.

It's possible that there's minor variation in the list of
operations; any operation involving any man or any woman
*after* they've been matched with a *yes* is extraneous.
So you can add or remove them all you like without affecting
the results.


## Version History


**0.8.3**

A slight bugfix for `print_datasets()`.   `print_datasets()`
prints out the keys for each value in sorted order.  But that
meant sorting the keys, and if you have keys of disparate
types, attempting to compare them with `<` or `>` could throw
a `ValueError`.  So `print_datasets()` now separates the keys
by type and sorts and prints each list of keys separately.

The dataset API allows you to set values that don't actually have
any keys mapping to them.  (You can call `dataset.value()`
with a value that you never pass in to `set()` or `set_keys()`.)
`correlate()` used to simply assert that every value had at
least one key; now it raises a `ValueError` with a string
that prints every value.  (This can be unreadable if there
are a lot!  But better safe than sorry.)

**0.8.2**

Fixed up ``infer_mv``.  It works the same, but the comments it
prints out are now much improved.  In particular, there was
a bug where it reported the same score for every match--the score
of the lowest-ranked match--instead of the correct score for each
match.

There were no other changes; the **correlate** algorithm is
unchanged from 0.8.1.

**0.8.1**

Fixed compatibility with Python 3.6.  All I needed to do was
remove some *equals-sign-in-f-strings* usage in spots.

**0.8**

The result of loving hand-tuned optimization: **correlate** version 0.8
is now an astonishing *19.5%* faster than version 0.7--and *27.3%* faster
than version 0.5!

The statistics have been improved, including some useful timing information.
This really demonstrates how much slower fuzzy keys are.

(To see for yourself, run `python3 tests/ytjd.test.py -v` and compare
the slowest test to the fastest, using the same corpus.  On my computer
the test without fuzzy keys is *12x faster* than the one that uses
fuzzy keys for everything.)

**0.7**

Careful micro-optimizations for both exact and fuzzy key
code paths have made **correlate** up to 7.5% faster!

The `MatchBoiler` was made even more ridiculously stable.
It should now always:

* return `results` in the same order they appeared in in `matches`, and
* prefer the *last* equivalent item when two or more items
  produce the same cumulative score.

**0.6.1**

Bugfix for major but rare bug: if there are multiple
groups of `len() > 1` of "connected" match objects with
the same score, the match boiler would only keep the
smallest one--the rest were accidentally discarded.
(`match_boiler_2_test()` was added to `tests/regression_test.py`
to check for this.)

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
In the early days of **correlate**, it didn't understand rounds; if you mapped the same
key to the same value twice, it only remembered one mapping, the one with the
highest weight.  Later I added rounds but they didn't seem to add much signal.
I thought redundant keys were uninteresting.  So I added `key_reuse_penalty_factor`.
That let you turn down the signal they provided, in case it
was adding more noise than actual useful signal.
It wasn't until the realization that `key->value` in round 0 and `key->value`
in round 1 were conceptually *two different keys* that I really understood
how redundant mappings of the same key to the same value should work.  And
once rounds maintained distinct counts of `keys / scores` for the scoring
formula, redundant keys in different rounds became *way* more informative.
I now think `key_reuse_penalty_factor` is dumb and worse than useless and
I've removed it.  If you think `key_reuse_penalty_factor` is useful,
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
