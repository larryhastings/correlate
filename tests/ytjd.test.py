#!/usr/bin/env python3
#
# correlate
# Copyright 2019-2020 by Larry Hastings
#
#
#
# Part of the "correlate" package:
# http://github.com/larryhastings/correlate

import correlate
import datetime
import functools
import os.path
import pprint
import sys
import time

from rapidfuzz.fuzz import ratio

def usage(error=None):
    if error:
        print(f"Error: {error}")
        print()
    print(f"usage: {os.path.basename(sys.argv[0])} [-v|--verbose] [<test-number> [<stop-test-number>]]")
    print()
    print("Runs tests using the Yours Truly, Johnny Dollar episode title test corpus.")
    print()
    print("By defualt it runs all tests; if you specify a single number as an option,")
    print("it runs only that test; if you specify two numbers it runs those tests and")
    print("all tests in-between.")
    print()
    print("Specifying -v or --verbose increases the amount of output.")
    print("There are two verbosity levels.")
    sys.exit(0)

def main(argv):
    # sorted from fastest to slowest
    # as observed on my workstation
    tests = [

        {
        "dataset_b": "script_first_pages",
        "use_fuzzy_search_for_title": False,
        "use_episode_number_as_ranking": True,
        },

        {
        "dataset_b": "best",
        "use_fuzzy_search_for_title": False,
        "use_episode_number_as_ranking": True,
        },

        {
        "dataset_b": "script_first_pages",
        "use_fuzzy_search_for_title": False,
        "use_episode_number_as_ranking": False,
        "minimum_score": 0.2,
        },

        {
        "dataset_b": "best",
        "use_fuzzy_search_for_title": False,
        "use_episode_number_as_ranking": False,
        },

        {
        "dataset_b": "script_first_pages",
        "use_fuzzy_search_for_title": True,
        "use_episode_number_as_ranking": True,
        "minimum_score": 0.1,
        },

        {
        "dataset_b": "best",
        "use_fuzzy_search_for_title": True,
        "use_episode_number_as_ranking": True,
        },

        {
        "dataset_b": "script_first_pages",
        "use_fuzzy_search_for_title": True,
        "use_episode_number_as_ranking": False,
        "minimum_score": 0.2,
        },

        {
        "dataset_b": "best",
        "use_fuzzy_search_for_title": True,
        "use_episode_number_as_ranking": False,
        },

    ]

    verbose = 0
    start = 0
    end = len(tests)

    while argv and argv[0].startswith("-"):
        arg = argv.pop(0)
        if arg in {'-v', '--verbose'}:
            verbose += 1
            continue
        usage(f"unknown flag {arg}")

    if len(argv):
        start = int(argv[0])
        if len(argv) > 1:
            end = int(argv[1])
        else:
            end = start


    for i, flags in enumerate(tests):
        if not (start <= i <= end):
            continue
        if verbose:
            print(f'"Yours Truly, Johnny Dollar" test #{i}')
            pprint.pprint(flags)
            print()
        t = YTJDTest()
        t.__dict__.update(flags)
        t(verbose)
    return 0

class YTJDTest:

    def __init__(self):
        self.dataset_a=None
        self.dataset_b=None

        self.use_fuzzy_search_for_title = False

        # use_fuzzy_search_for_title = False
        self.exact_title_key_weight = 1

        # use_fuzzy_search_for_title = True
        self.fuzzy_title_weight = 8
        self.fuzzy_title_minimum_score = 0.5
        self.fuzzy_title_score_power = 3

        self.episode_date_weight = 1

        self.use_episode_number_as_ranking = True

        # use_episode_number_as_ranking = False
        self.episode_number_weight = 1

        self.score_ratio_bonus = 0.5
        self.minimum_score = 0
        self.ranking_factor = 0.4

        self.c = correlate.Correlator()

        self.print_matches = False

    def __call__(self, verbose):
        dataset_lookup = {
            "database": self.dataset_database,
            "best": self.dataset_best,
            "script_first_pages": self.dataset_script_first_pages,
        }

        if not self.use_episode_number_as_ranking:
            self.ranking_factor = 0.0

        self.dataset_a = self.dataset_a or "database"
        dataset_lookup[self.dataset_a](self.c.dataset_a)

        self.dataset_b = self.dataset_b or "best"
        dataset_lookup[self.dataset_b](self.c.dataset_b)

        # map correct matches going from a to b
        correct_matches = [None] * len(self.c.dataset_a.values)
        for index_b, index_a in enumerate(self.c.dataset_b.correct_matches):
            if index_a is not None:
                correct_matches[index_a] = index_b

        start = time.perf_counter()
        result = self.c.correlate(
            ranking_factor=self.ranking_factor,
            minimum_score=self.minimum_score,
            score_ratio_bonus=self.score_ratio_bonus,
            )
        end = time.perf_counter()
        if verbose:
            print(f"elapsed time: {end - start} seconds")
            print()

        return_value = 0

        prefix="    "

        if verbose > 1:
            print("matches:")
            for match in result.matches:
                print(f"{prefix}{match.score}")
                print_ytjd(match.value_a, prefix=prefix)
                print_ytjd(match.value_b, prefix=prefix)
                print()

        for match in result.matches:
            index_a = self.c.dataset_a.lines.index(match.value_a)
            index_b = self.c.dataset_b.lines.index(match.value_b)
            correct_match = correct_matches[index_a]
            if correct_match != index_b:
                print("mismatch!")
                print(f"{prefix}{match.score}")
                print(f"{prefix}this value in a:")
                print_ytjd(match.value_a, prefix=prefix)
                print(f"{prefix}matched this value in b:")
                print_ytjd(match.value_b, prefix=prefix)
                if correct_match is not None:
                    print(f"{prefix}but should have matched this other value in b:")
                    print_ytjd(self.c.dataset_b.lines[correct_match], prefix=prefix)
                else:
                    print(f"{prefix}but shouldn't have matched anything!")
                print()
                return_value += 1

        # print("UNMATCHED B", result.unmatched_b)
        for unmatched in result.unmatched_b:
            index_b = self.c.dataset_b.lines.index(unmatched)
            correct_match = self.c.dataset_b.correct_matches[index_b]
            if correct_match is not None:
                print("failed match!")
                print(f"{prefix}this value in a:")
                print_ytjd(self.c.dataset_a.lines[correct_match], prefix=prefix)
                print(f"{prefix}should have matched this value in b:")
                print_ytjd(unmatched, prefix=prefix)
                print(f"{prefix}but instead the value in b didn't match anything.")
                print()
                return_value += 1

        return return_value

    def dataset_database(self, dataset):
        dataset.lines = database_lines
        for i, original_line in enumerate(dataset.lines):
            line = cleanup_line(original_line)
            # print(f"DATABASE {original_line=} {line=}")
            self.set_line(dataset, original_line, line)
            dataset.value(original_line, ranking=i)

    def dataset_best(self, dataset):
        correct_matches = dataset.correct_matches = []
        dataset.lines = best_lines
        for i, original_line in enumerate(dataset.lines):
            line, _, correct_match = original_line.rpartition(" | ")
            line = line.replace(".flac", "")
            line = line.replace(".mp3", "")
            line = cleanup_line(line)
            # print(f"BEST {original_line=} {line=}")
            self.set_line(dataset, original_line, line)
            dataset.value(original_line, ranking=i)
            correct_matches.append(int(correct_match))

    def dataset_script_first_pages(self, dataset):
        correct_matches = dataset.correct_matches = []
        dataset.lines = script_first_pages_lines
        for i, original_line in enumerate(dataset.lines):
            line, _, correct_match = original_line.rpartition(" | ")
            line = line.replace(".jpg", "")
            line = cleanup_line(line)
            # print(f"SCRIPT_FIRST_PAGES {original_line=} {line=}")
            self.set_line(dataset, original_line, line)
            dataset.value(original_line, ranking=i)
            correct_match = correct_match.strip()
            if correct_match == "-":
                correct_match = None
            else:
                correct_match = int(correct_match)
            correct_matches.append(correct_match)

        # minimum_score = 0.4


    def set_line(self, dataset, original_line, line):
        # line = line.lower().strip()

        def set_episode_number(number, value):
            if self.use_episode_number_as_ranking:
                delta = 0
                if number.startswith("s"):
                    number = number[1:]
                    delta = 1000
                dataset.value(value, ranking=int(number) + delta)
            else:
                episode = EpisodeFuzzyKey(number)
                dataset.set(episode, value, weight=self.episode_number_weight)

        fields = line.split(" - ")
        for field in fields:
            if field.startswith("19") and "-" in field:
                field, _, part = field.partition(" ")
                if _:
                    # dang it there are a couple dates with a "part" number in them
                    part = part.strip()
                    dataset.set(part, original_line)
                    field = field.strip()

                broadcast_date = field
                date = DateFuzzyKey(broadcast_date)
                dataset.set(date, original_line, weight=self.episode_date_weight)
                # dataset.set(broadcast_date, original_line, weight=1)
                continue

            if field.startswith("s") and is_int(field[1:]):
                # field = field[1:]
                set_episode_number(field, original_line)
                continue

            if is_int(field):
                set_episode_number(field, original_line)
                # episode_number = int(field)
                # use_episode_number = episode_number >= 10
                # # remove leading zeroes
                # episode_number = str(episode_number)
                # if use_episode_number:
                #     # episode numbers less than 10 can result in bad matches,
                #     # there are occasional random single-digit numbers floating
                #     # around in the data
                #     dataset.set(episode_number, original_line, weight=0.5)
                continue

            if self.use_fuzzy_search_for_title:
                # split alternate titles into separate fuzzy keys
                for subtitle in field.split(" aka "):
                    # print(f"    string used for fuzzy match {field!r}")
                    key = StringFuzzyKey(subtitle, minimum_score=self.fuzzy_title_minimum_score, score_power=self.fuzzy_title_score_power)
                    # print(f"    {dataset._id=} {field=} {key=} -> {original_line=}")
                    dataset.set(key, original_line, weight=self.fuzzy_title_weight)
            else:
                # don't remove dashes until now, it messes up dates, etc
                field = field.replace("-", " ")
                field = field.replace("aka", " ")
                dataset.set_keys(field.lower().split(), original_line, weight=self.exact_title_key_weight)




def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def cleanup_line(line):
    # remove
    for s in (
        "Yours Truly, Johnny Dollar - ",
        " Matter",
        ):
        line = line.replace(s, "")

    # replace with space
    for s in (
        " The ",
        " Part ",
        ",",
        ".",
        "(",
        ")",
        "'s",
        "'",
        ):
        line = line.replace(s, " ")
    line = " ".join(line.strip().split())
    return line


class DateFuzzyKey(correlate.FuzzyKey):
    def __repr__(self):
        return f"<DateFuzzyKey {self.date}>"
    def __init__(self, date):
        year, month, day = date.split("-")
        year = int(year)
        month = int(month)
        day = int(day)
        self.date = date
        self.datetime = datetime.date(year, month, day)

    def compare(self, other):
        # if 1 <= delta <= 5 days, return 1 - (delta / 10)
        # if 5 < delta <= 8 days, return 0.5 (one week off for Sunday shows)
        # else return 0
        delta = self.datetime - other.datetime
        days = abs(delta.days)
        assert days
        if days <= 5:
            return 1.0 - (days * 0.15)
        if days <= 8:
            return 0.25
        return 0

_DateFuzzyKey = DateFuzzyKey
DateFuzzyKey = functools.lru_cache(maxsize=2**16)(DateFuzzyKey)


class EpisodeFuzzyKey(correlate.FuzzyKey):
    def __repr__(self):
        return f"<EpisodeFuzzyKey {self.episode}>"
    def __init__(self, episode):
        self.episode = episode
        self.special = episode.startswith('s')
        if self.special:
            episode = episode[1:]
        self.number = int(episode)

    def compare(self, other):
        # fuzzy key supports guarantee that
        # we'll never call compare if "self is other".
        # so by definition self and other are different keys.
        # and since we use an lru cache that keys on the inputs,
        # if self.episode == other.episode, then self.special and
        # other.special must be different, and therefore these
        # are definitely different episodes.
        if self.episode == other.episode:
            assert self.special != other.special
            return 0.0
        delta = abs(self.number - other.number)
        if delta >= 5:
            return 0.0
        return 1.0 - (delta / 5)

_EpisodeFuzzyKey = EpisodeFuzzyKey
EpisodeFuzzyKey = functools.lru_cache(maxsize=2**16)(EpisodeFuzzyKey)


class StringFuzzyKey(correlate.FuzzyKey):
    def __repr__(self):
        return f"<StringFuzzyKey {self.s!r}>"

    def __init__(self, s, *, minimum_score, score_power):
        self.s = s
        self.lower_s = s.lower()
        self.minimum_score = minimum_score
        self.score_power = score_power

    def compare(self, other):
        score = (ratio(self.lower_s, other.lower_s) / 100) - self.minimum_score
        if score < 0:
            return 0.0
        score = score / (1.0 - self.minimum_score)
        score = score ** self.score_power
        return score

_StringFuzzyKey = StringFuzzyKey
StringFuzzyKey = functools.lru_cache(maxsize=2**16)(StringFuzzyKey)

# DateFuzzyKey = EpisodeFuzzyKey = lambda s: s


uninteresting_title = "Yours Truly, Johnny Dollar - "
def print_ytjd(s, prefix=""):
    fields = s.partition(" | ")[0].strip().rpartition("/")[2].replace(uninteresting_title, "").split(" - ")

    date = number = title = None

    for field in fields:
        field = field.strip()
        if is_int(field) or (field[0] == "s" and is_int(field[1:])):
            assert number is None, f"{number=} - {date=} - {title=}, {field=}, {s=!r}"
            number = field
            continue
        if field[0].isalpha():
            assert title is None, f"{number=} - {date=} - {title=}, {field=}, {s=!r}"
            title = field
            continue
        if len(field) >= 5:
            assert date is None, f"{number=} - {date=} - {title=}, {field=}, {s=!r}"
            assert field[:3] in ("194", "195", "196")
            date = field
            continue

    print(f"{prefix}    {number} - {date} - {title}")




database_lines = """
s01 - 1948-12-06 - Yours Truly, Lloyd London
s02 - 1948-12-07 - Milford Brooks III
001 - 1949-02-18 - The Parakoff Policy
002 - 1949-02-25 - The Slow Boat From China
003 - 1949-03-04 - The Robert Perry Case
004 - 1949-03-11 - Murder Is A Merry-Go-Round
005 - 1949-03-25 - Milford Brooks III Matter
006 - 1949-04-01 - The Stolen Portrait Of The Duke Of Massen
007 - 1949-04-08 - The Thespia Theatre Bonfire aka The Case Of The Foxy Terrier
008 - 1949-04-15 - The Case Of The Hundred Thousand Dollar Legs
009 - 1949-04-22 - The Case Of Barton Drake
010 - 1949-07-17 - Here Comes The Death Of The Party aka The Case Of The Poisonous Grapevine
011 - 1949-07-24 - Who Took The Taxis For A Ride
012 - 1949-07-31 - How Much Bourbon Can Flow Under The Bridgework?
013 - 1949-08-07 - Murder Ain't Minor aka The Case Of Bonnie Goodwin
014 - 1949-08-14 - How Not To Take A Vacation In Fairfax, Virginia aka Death Takes A Working Day
015 - 1949-08-21 - Out Of The Fire, Into The Frying Pan aka The Prize Hog Bodyguard
016 - 1949-08-28 - How I Turned A Luxury Liner Into A Battleship
017 - 1949-09-04 - The Expiring Nickels And The Egyptian Jackpot
018 - 1949-09-25 - The Search For Michelle Marsh
019 - 1949-10-01 - The Fishing Boat Affair
020 - 1949-10-08 - The Racehorse Piledriver Matter
021 - 1949-10-15 - Dr. Otto Schmedlich
022 - 1949-10-22 - Witness, Witness, Who's Got The Witness
023 - 1949-10-29 - The Little Man Who Wasn't All There
024 - 1949-11-05 - The Island Of Tin-Yutan aka The South Sea Adventure
025 - 1949-11-12 - The Melanie Carter Matter aka Who'd Like To Rock The Old Doll To Sleep
026 - 1949-11-26 - The Skull Canyon Mine
027 - 1949-12-03 - Bodyguard To Anne Connelly
028 - 1949-12-10 - The Circus Animal Show Matter
029 - 1949-12-17 - Haiti Adventure Matter
030 - 1949-12-24 - How I Played Santa Claus And Almost Got Left Holding The Bag
031 - 1949-12-31 - The Diamond Protector Matter aka You Lead A Diamond, Mother, And The Game Will Really Get Started
032 - 1950-01-07 - The Firebug Hunter Matter aka Press Out My Asbestos Dinner Jacket, Mother, I'm Going To Smoke
033 - 1950-01-14 - The Missing Chinese Stripper Matter aka The Search For The Missing Chinese Stripper Wu Sin aka She Didn't Have Much To Hide, So Why Did They Hide Her? aka This Time I Went On A Personally Conducted Tour Of San Francisco And Johnny Dollar Got A New Slant On Life
034 - 1950-02-03 - Death Takes A Working Day aka The Loyal B. Martin Matter
035 - 1950-02-10 - The S.S. Malay Trader Ship
036 - 1950-02-17 - The Gravedigger's Spades aka Mr. & Mrs. Arbuthnel Trump
037 - 1950-02-24 - The Archeologist aka The Disappearance Of Bruce Lambert
038 - 1950-03-03 - Bodyguard To The Late Robert W. Perry
039 - 1950-03-07 - Alec Jefferson, The Youthful Millionaire aka Rebel Wildcatters
040 - 1950-03-14 - The Eighty-Five Little Minks
041 - 1950-03-21 - The Man Who Wrote Himself To Death aka Stuart Palmer, Writer
042 - 1950-03-28 - The Village Scene Matter aka The Missing Masterpiece
043 - 1950-04-04 - The Story Of The Big Red Schoolhouse
044 - 1950-04-11 - The Dead First-Helpers
045 - 1950-04-18 - The Story Of The Ten-O-Eight aka The Story Of The 10:08
046 - 1950-04-25 - Pearl Carrasa
047 - 1950-05-02 - The Able Tackitt Matter
048 - 1950-05-09 - The Harold Trandem Matter
049 - 1950-05-16 - The Sidney Rykoff Matter
050 - 1950-05-23 - The Earl Chadwick Matter
051 - 1950-05-30 - The Port-au-Prince Matter
052 - 1950-06-08 - The Caligio Diamond Matter
053 - 1950-06-15 - The Arrowcraft Matter
054 - 1950-06-22 - The London Matter
055 - 1950-06-29 - The Barbara James Matter
056 - 1950-07-06 - The Belo-Horizonte Railroad
057 - 1950-07-13 - The Calgary Matter
058 - 1950-07-20 - The Henry J. Unger Matter
059 - 1950-07-27 - The Tell-All Book Matter
060 - 1950-08-03 - The Blood River Matter
061 - 1950-08-10 - The Hartford Alliance Matter
062 - 1950-08-17 - The Mickey McQueen Matter
063 - 1950-08-22 - The Trans-Pacific Import Export Company, South China Branch Matter (unaired rehearsal)
064 - 1950-08-31 - The Virginia Beach Matter
065 - 1950-09-30 - The Howard Caldwell Matter
066 - 1950-10-07 - The Richard Splain Matter
067 - 1950-10-14 - The Yankee Pride Matter
068 - 1950-10-21 - The Jack Madigan Matter
069 - 1950-10-28 - The Joan Sebastian Matter
070 - 1950-11-04 - The Queen Anne Pistols Matter
071 - 1950-11-11 - The Adam Kegg Matter
072 - 1950-11-18 - The Nora Falkner Matter
073 - 1950-11-25 - The Woodward, Manila Matter
074 - 1950-12-15 - The Leland Blackburn Matter
075 - 1950-12-23 - The Montevideo Matter
076 - 1950-12-30 - The Rudy Valentine Matter
077 - 1951-01-06 - The Adolph Shoman Matter
078 - 1951-01-13 - The Port-O-Call Matter aka The Port O' Call Matter
079 - 1951-01-20 - The David Rockey Matter
080 - 1951-01-27 - The Weldon Bragg Matter
081 - 1951-02-03 - The Monopoly Matter
082 - 1951-02-10 - The Lloyd Hammerly Matter
083 - 1951-02-17 - The Vivian Fair Matter
084 - 1951-02-24 - The Jarvis Wilder Matter
085 - 1951-03-03 - The Celia Woodstock Matter
086 - 1951-03-10 - The Stanley Springs Matter
087 - 1951-03-17 - The Emil Lovett Matter
088 - 1951-03-24 - The Byron Hayes Matter
089 - 1951-03-31 - The Jackie Cleaver Matter
090 - 1951-04-07 - The Edward French Matter
091 - 1951-04-14 - The Mickey McQueen Matter
092 - 1951-04-21 - The Willard South Matter
093 - 1951-04-28 - The Month-End Raid Matter
094 - 1951-05-05 - The Virginia Towne Matter
095 - 1951-05-12 - The Marie Meadows Matter
096 - 1951-05-19 - The Jane Doe Matter
097 - 1951-05-26 - The Lillis Bond Matter
098 - 1951-06-02 - The Soderbury, Maine Matter
099 - 1951-06-09 - The George Farmer Matter
100 - 1951-06-16 - The Arthur Boldrick Matter
101 - 1951-06-20 - The Malcolm Wish, M.D. Matter
102 - 1951-06-27 - The Hatchet House Theft Matter
103 - 1951-07-04 - The Alonzo Chapman Matter
104 - 1951-07-11 - The Fair-Way Matter
105 - 1951-07-18 - The Neal Breer Matter
106 - 1951-07-25 - The Blind Item Matter
107 - 1951-08-01 - The Horace Lockhart Matter
108 - 1951-08-08 - The Morgan Fry Matter
109 - 1951-08-15 - The Lucky Costa Matter
110 - 1951-08-22 - The Cumberland Theft Matter
111 - 1951-08-29 - The Leland Case Matter
112 - 1951-09-12 - The Rum Barrel Matter
113 - 1951-09-19 - The Cuban Jewel Matter
114 - 1951-09-26 - The Protection Matter
115 - 1951-10-06 - The Douglas Taylor Matter
116 - 1951-10-13 - The Millard Ward Matter
117 - 1951-10-20 - The Janet Abbe Matter
118 - 1951-10-27 - The Tolhurst Theft Matter
119 - 1951-11-03 - The Hannibal Murphy Matter
120 - 1951-11-10 - The Birdy Baskerville Matter
121 - 1951-11-17 - The Merrill Kent Matter
122 - 1951-12-08 - The Youngstown Credit Group Matter
123 - 1951-12-15 - The Paul Barberis Matter
124 - 1951-12-22 - The Maynard Collins Matter
125 - 1951-12-29 - The Alma Scott Matter
126 - 1952-01-05 - The Glen English Matter
127 - 1952-01-12 - The Baxter Matter
128 - 1952-07-02 - The Amelia Harwell Matter
129 - 1952-07-16 - The Henry Page Matter
130 - 1952-07-30 - The New Bedford Morgue Matter
131 - 1952-08-06 - The Sidney Mann Matter
132 - 1952-08-13 - The Tom Hickman Matter
133 - 1952-08-20 - The Edith Maxwell Matter
134 - 1952-08-27 - The Yankee Pride Matter
135 - 1952-09-03 - The Montevideo Matter
s03 - 1952-11-24 - The Trans-Pacific Matter, Part 1
s04 - 1952-11-24 - The Trans-Pacific Matter, Part 2
136 - 1952-11-28 - The Singapore Arson Matter
137 - 1952-12-05 - The James Clayton Matter
138 - 1952-12-12 - The Elliott Champion Matter
139 - 1952-12-19 - The New Cambridge Matter
140 - 1952-12-26 - The Walter Patterson Matter
141 - 1953-01-02 - The Baltimore Matter
142 - 1953-01-09 - The Thelma Ibsen Matter
143 - 1953-01-16 - The Starlet Matter
144 - 1953-01-23 - The Marigold Matter
145 - 1953-01-30 - The Kay Bellamy Matter
146 - 1953-02-06 - The Chicago Fraud Matter
147 - 1953-02-13 - The Lancer Jewelry Matter
148 - 1953-02-20 - The Latourette Matter
149 - 1953-02-27 - The Underwood Matter
150 - 1953-03-06 - The Jeanne Maxwell Matter
151 - 1953-03-10 - The Birdy Baskerville Matter
152 - 1953-03-17 - The King's Necklace Matter
153 - 1953-03-24 - The Syndicate Matter
154 - 1953-03-31 - The Lester James Matter
155 - 1953-04-07 - The Enoch Arden Matter
156 - 1953-04-14 - The Madison Matter
157 - 1953-04-21 - The Dameron Matter
158 - 1953-04-28 - The San Antonio Matter
159 - 1953-05-05 - The Blackmail Matter
160 - 1953-05-12 - The Rochester Theft Matter
161 - 1953-05-19 - The Emily Braddock Matter
162 - 1953-05-26 - The Brisbane Fraud Matter
163 - 1953-06-02 - The Costain Matter
164 - 1953-06-09 - The Oklahoma Red Matter
165 - 1953-06-16 - The Emil Carter Matter
166 - 1953-06-23 - The Jonathan Bellows Matter
167 - 1953-06-30 - The Jones Matter
168 - 1953-07-07 - The Bishop Blackmail Matter
169 - 1953-07-14 - The Shayne Bombing Matter
170 - 1953-07-21 - The Black Doll Matter
171 - 1953-07-28 - The James Forbes Matter
172 - 1953-08-04 - The Voodoo Matter
173 - 1953-08-11 - The Nancy Shaw Matter
174 - 1953-08-18 - The Isabelle James Matter aka The Kimball Matter
175 - 1953-08-25 - The Nelson Matter
176 - 1953-09-01 - The Stanley Price Matter
177 - 1953-09-08 - The Lester Matson Matter
178 - 1953-09-15 - The Oscar Clark Matter
179 - 1953-09-22 - The William Post Matter
180 - 1953-09-29 - The Amita Buddha Matter
181 - 1953-10-06 - The Alfred Chambers Matter
182 - 1953-10-13 - The Phillip Morey Matter
183 - 1953-10-20 - The Allen Saxton Matter
184 - 1953-10-27 - The Howard Arnold Matter
185 - 1953-11-03 - The Gino Gambona Matter
186 - 1953-11-10 - The Bobby Foster Matter
187 - 1953-11-17 - The Nathan Gayles Matter
188 - 1953-11-24 - The Independent Diamond Traders' Matter
189 - 1953-12-01 - The Monopoly Matter
190 - 1953-12-08 - The Barton Baker Matter
191 - 1953-12-15 - The Milk And Honey Matter
192 - 1953-12-22 - The Rudy Valentine Matter
193 - 1953-12-29 - The Ben Bryson Matter
194 - 1954-01-05 - The Fair-Way Matter
195 - 1954-01-12 - The Celia Woodstock Matter
196 - 1954-01-19 - The Draminski Matter
197 - 1954-01-26 - The Beauregard Matter
198 - 1954-02-02 - The Paul Gorrell Matter
199 - 1954-02-09 - The Harpooned Angler Matter
200 - 1954-02-16 - The Uncut Canary Matter
201 - 1954-02-23 - The Classified Killer Matter
202 - 1954-03-02 - The Road-Test Matter
203 - 1954-03-09 - The Terrified Taun Matter
204 - 1954-03-16 - The Berlin Matter
205 - 1954-03-23 - The Piney Corners Matter
206 - 1954-03-30 - The Undried Fiddle Back Matter
207 - 1954-04-06 - The Sulphur And Brimstone Matter
208 - 1954-04-13 - The Magnolia And Honeysuckle Matter
209 - 1954-04-20 - The Nathan Swing Matter
210 - 1954-04-27 - The Frustrated Phoenix Matter
211 - 1954-05-04 - The Dan Frank Matter
212 - 1954-05-11 - The Aromatic Cicatrix Matter
213 - 1954-05-18 - The Bilked Baroness Matter
214 - 1954-05-25 - The Punctilious Firebug Matter
215 - 1954-06-01 - The Temperamental Tote Board Matter
216 - 1954-06-08 - The Sara Dearing Matter
217 - 1954-06-15 - The Paterson Transport Matter
218 - 1954-06-22 - The Arthur Boldrick Matter
219 - 1954-06-29 - The Woodward, Manila Matter
220 - 1954-07-06 - The Jan Brueghel Matter aka The Flowering Judas Matter
221 - 1954-07-13 - The Carboniferous Dolomite Matter
222 - 1954-07-20 - The Jeanne Maxwell Matter
223 - 1954-07-27 - The Radioactive Gold Matter
224 - 1954-08-03 - The Hampton Line Matter
225 - 1954-08-10 - The Sarah Martin Matter
226 - 1954-09-05 - The Hamilton Payroll Matter
227 - 1954-09-12 - The Great Bannock Race Matter
228 - 1954-09-19 - The Upjohn Matter
s05 - 1955-08-29 - The Trans-Pacific Import-Export Matter
229 - 1955-10-03 - The Macormack Matter, Part 1
230 - 1955-10-04 - The Macormack Matter, Part 2
231 - 1955-10-05 - The Macormack Matter, Part 3
232 - 1955-10-06 - The Macormack Matter, Part 4
233 - 1955-10-07 - The Macormack Matter, Part 5
234 - 1955-10-10 - The Molly K Matter, Part 1
235 - 1955-10-11 - The Molly K Matter, Part 2
236 - 1955-10-12 - The Molly K Matter, Part 3
237 - 1955-10-13 - The Molly K Matter, Part 4
238 - 1955-10-14 - The Molly K Matter, Part 5
239 - 1955-10-17 - The Chesapeake Fraud Matter, Part 1
240 - 1955-10-18 - The Chesapeake Fraud Matter, Part 2
241 - 1955-10-19 - The Chesapeake Fraud Matter, Part 3
242 - 1955-10-20 - The Chesapeake Fraud Matter, Part 4
243 - 1955-10-21 - The Chesapeake Fraud Matter, Part 5
244 - 1955-10-24 - The Alvin Summers Matter, Part 1
245 - 1955-10-25 - The Alvin Summers Matter, Part 2
246 - 1955-10-26 - The Alvin Summers Matter, Part 3
247 - 1955-10-27 - The Alvin Summers Matter, Part 4
248 - 1955-10-28 - The Alvin Summers Matter, Part 5
249 - 1955-10-31 - The Valentine Matter, Part 1
250 - 1955-11-01 - The Valentine Matter, Part 2
251 - 1955-11-02 - The Valentine Matter, Part 3
252 - 1955-11-03 - The Valentine Matter, Part 4
253 - 1955-11-04 - The Valentine Matter, Part 5
254 - 1955-11-07 - The Lorko Diamonds Matter, Part 1
255 - 1955-11-08 - The Lorko Diamonds Matter, Part 2
256 - 1955-11-09 - The Lorko Diamonds Matter, Part 3
257 - 1955-11-10 - The Lorko Diamonds Matter, Part 4
258 - 1955-11-11 - The Lorko Diamonds Matter, Part 5
259 - 1955-11-14 - The Broderick Matter, Part 1
260 - 1955-11-15 - The Broderick Matter, Part 2
261 - 1955-11-16 - The Broderick Matter, Part 3
262 - 1955-11-17 - The Broderick Matter, Part 4
263 - 1955-11-18 - The Broderick Matter, Part 5
264 - 1955-11-21 - The Amy Bradshaw Matter, Part 1
265 - 1955-11-22 - The Amy Bradshaw Matter, Part 2
266 - 1955-11-23 - The Amy Bradshaw Matter, Part 3
267 - 1955-11-24 - The Amy Bradshaw Matter, Part 4
268 - 1955-11-25 - The Amy Bradshaw Matter, Part 5
269 - 1955-11-28 - The Henderson Matter, Part 1
270 - 1955-11-29 - The Henderson Matter, Part 2
271 - 1955-11-30 - The Henderson Matter, Part 3
272 - 1955-12-01 - The Henderson Matter, Part 4
273 - 1955-12-02 - The Henderson Matter, Part 5
274 - 1955-12-05 - The Cronin Matter, Part 1
275 - 1955-12-06 - The Cronin Matter, Part 2
276 - 1955-12-07 - The Cronin Matter, Part 3
277 - 1955-12-08 - The Cronin Matter, Part 4
278 - 1955-12-09 - The Cronin Matter, Part 5
279 - 1955-12-12 - The Lansing Fraud Matter, Part 1
280 - 1955-12-13 - The Lansing Fraud Matter, Part 2
281 - 1955-12-14 - The Lansing Fraud Matter, Part 3
282 - 1955-12-15 - The Lansing Fraud Matter, Part 4
283 - 1955-12-16 - The Lansing Fraud Matter, Part 5
284 - 1955-12-19 - The Nick Shurn Matter, Part 1
285 - 1955-12-20 - The Nick Shurn Matter, Part 2
286 - 1955-12-21 - The Nick Shurn Matter, Part 3
287 - 1955-12-22 - The Nick Shurn Matter, Part 4
288 - 1955-12-23 - The Nick Shurn Matter, Part 5
289 - 1955-12-26 - The Forbes Matter, Part 1
290 - 1955-12-27 - The Forbes Matter, Part 2
291 - 1955-12-28 - The Forbes Matter, Part 3
292 - 1955-12-29 - The Forbes Matter, Part 4
293 - 1955-12-30 - The Forbes Matter, Part 5
294 - 1956-01-02 - The Caylin Matter, Part 1
295 - 1956-01-03 - The Caylin Matter, Part 2
296 - 1956-01-04 - The Caylin Matter, Part 3
297 - 1956-01-05 - The Caylin Matter, Part 4
298 - 1956-01-06 - The Caylin Matter, Part 5
299 - 1956-01-09 - The Todd Matter, Part 1
300 - 1956-01-10 - The Todd Matter, Part 2
301 - 1956-01-11 - The Todd Matter, Part 3
302 - 1956-01-12 - The Todd Matter, Part 4
303 - 1956-01-13 - The Todd Matter, Part 5
304 - 1956-01-16 - The Ricardo Amerigo Matter, Part 1
305 - 1956-01-17 - The Ricardo Amerigo Matter, Part 2
306 - 1956-01-18 - The Ricardo Amerigo Matter, Part 3
307 - 1956-01-19 - The Ricardo Amerigo Matter, Part 4
308 - 1956-01-20 - The Ricardo Amerigo Matter, Part 5
309 - 1956-01-23 - The Duke Red Matter, Part 1
310 - 1956-01-24 - The Duke Red Matter, Part 2
311 - 1956-01-25 - The Duke Red Matter, Part 3
312 - 1956-01-26 - The Duke Red Matter, Part 4
313 - 1956-01-27 - The Duke Red Matter, Part 5
314 - 1956-01-30 - The Flight Six Matter, Part 1
315 - 1956-01-31 - The Flight Six Matter, Part 2
316 - 1956-02-01 - The Flight Six Matter, Part 3
317 - 1956-02-02 - The Flight Six Matter, Part 4
318 - 1956-02-03 - The Flight Six Matter, Part 5
319 - 1956-02-06 - The McClain Matter, Part 1
320 - 1956-02-07 - The McClain Matter, Part 2
321 - 1956-02-08 - The McClain Matter, Part 3
322 - 1956-02-09 - The McClain Matter, Part 4
323 - 1956-02-10 - The McClain Matter, Part 5
324 - 1956-02-13 - The Cui Bono Matter, Part 1
325 - 1956-02-14 - The Cui Bono Matter, Part 2
326 - 1956-02-15 - The Cui Bono Matter, Part 3
327 - 1956-02-16 - The Cui Bono Matter, Part 4
328 - 1956-02-17 - The Cui Bono Matter, Part 5
329 - 1956-02-20 - The Bennet Matter, Part 1
330 - 1956-02-21 - The Bennet Matter, Part 2
331 - 1956-02-22 - The Bennet Matter, Part 3
332 - 1956-02-23 - The Bennet Matter, Part 4
333 - 1956-02-24 - The Bennet Matter, Part 5
334 - 1956-02-27 - The Fathom-Five Matter, Part 1
335 - 1956-02-28 - The Fathom-Five Matter, Part 2
336 - 1956-02-29 - The Fathom-Five Matter, Part 3
337 - 1956-03-01 - The Fathom-Five Matter, Part 4
338 - 1956-03-02 - The Fathom-Five Matter, Part 5
339 - 1956-03-05 - The Plantagent Matter, Part 1
340 - 1956-03-06 - The Plantagent Matter, Part 2
341 - 1956-03-07 - The Plantagent Matter, Part 3
342 - 1956-03-08 - The Plantagent Matter, Part 4
343 - 1956-03-09 - The Plantagent Matter, Part 5
344 - 1956-03-12 - The Clinton Matter, Part 1
345 - 1956-03-13 - The Clinton Matter, Part 2
346 - 1956-03-14 - The Clinton Matter, Part 3
347 - 1956-03-15 - The Clinton Matter, Part 4
348 - 1956-03-16 - The Clinton Matter, Part 5
349 - 1956-03-19 - The Jolly Roger Fraud Matter, Part 1
350 - 1956-03-20 - The Jolly Roger Fraud Matter, Part 2
351 - 1956-03-21 - The Jolly Roger Fraud Matter, Part 3
352 - 1956-03-22 - The Jolly Roger Fraud Matter, Part 4
353 - 1956-03-23 - The Jolly Roger Fraud Matter, Part 5
354 - 1956-03-26 - The Lamarr Matter, Part 1
355 - 1956-03-27 - The Lamarr Matter, Part 2
356 - 1956-03-28 - The Lamarr Matter, Part 3
357 - 1956-03-29 - The Lamarr Matter, Part 4
358 - 1956-03-30 - The Lamarr Matter, Part 5
359 - 1956-04-02 - The Salt City Matter, Part 1
360 - 1956-04-03 - The Salt City Matter, Part 2
361 - 1956-04-04 - The Salt City Matter, Part 3
362 - 1956-04-05 - The Salt City Matter, Part 4
363 - 1956-04-06 - The Salt City Matter, Part 5
364 - 1956-04-09 - The Laird Douglas Douglas Of Heatherscote Matter, Part 1
365 - 1956-04-10 - The Laird Douglas Douglas Of Heatherscote Matter, Part 2
366 - 1956-04-11 - The Laird Douglas Douglas Of Heatherscote Matter, Part 3
367 - 1956-04-12 - The Laird Douglas Douglas Of Heatherscote Matter, Part 4
368 - 1956-04-13 - The Laird Douglas Douglas Of Heatherscote Matter, Part 5
369 - 1956-04-16 - The Shepherd Matter, Part 1
370 - 1956-04-17 - The Shepherd Matter, Part 2
371 - 1956-04-18 - The Shepherd Matter, Part 3
372 - 1956-04-19 - The Shepherd Matter, Part 4
373 - 1956-04-20 - The Shepherd Matter, Part 5
374 - 1956-04-23 - The Lonely Hearts Matter, Part 1
375 - 1956-04-24 - The Lonely Hearts Matter, Part 2
376 - 1956-04-25 - The Lonely Hearts Matter, Part 3
377 - 1956-04-26 - The Lonely Hearts Matter, Part 4
378 - 1956-04-27 - The Lonely Hearts Matter, Part 5
379 - 1956-04-30 - The Callicles Matter, Part 1
380 - 1956-05-01 - The Callicles Matter, Part 2
381 - 1956-05-02 - The Callicles Matter, Part 3
382 - 1956-05-03 - The Callicles Matter, Part 4
383 - 1956-05-04 - The Callicles Matter, Part 5
384 - 1956-05-07 - The Silver Blue Matter, Part 1
385 - 1956-05-08 - The Silver Blue Matter, Part 2
386 - 1956-05-09 - The Silver Blue Matter, Part 3
387 - 1956-05-10 - The Silver Blue Matter, Part 4
388 - 1956-05-11 - The Silver Blue Matter, Part 5
389 - 1956-05-14 - The Matter Of The Medium, Well Done, Part 1
390 - 1956-05-15 - The Matter Of The Medium, Well Done, Part 2
391 - 1956-05-16 - The Matter Of The Medium, Well Done, Part 3
392 - 1956-05-17 - The Matter Of The Medium, Well Done, Part 4
393 - 1956-05-18 - The Matter Of The Medium, Well Done, Part 5
394 - 1956-05-21 - The Tears Of Night Matter, Part 1
395 - 1956-05-22 - The Tears Of Night Matter, Part 2
396 - 1956-05-23 - The Tears Of Night Matter, Part 3
397 - 1956-05-24 - The Tears Of Night Matter, Part 4
398 - 1956-05-25 - The Tears Of Night Matter, Part 5
399 - 1956-05-28 - The Matter Of Reasonable Doubt, Part 1
400 - 1956-05-29 - The Matter Of Reasonable Doubt, Part 2
401 - 1956-05-30 - The Matter Of Reasonable Doubt, Part 3
402 - 1956-05-31 - The Matter Of Reasonable Doubt, Part 4
403 - 1956-06-01 - The Matter Of Reasonable Doubt, Part 5
404 - 1956-06-04 - The Indestructible Mike Matter, Part 1
405 - 1956-06-05 - The Indestructible Mike Matter, Part 2
406 - 1956-06-06 - The Indestructible Mike Matter, Part 3
407 - 1956-06-07 - The Indestructible Mike Matter, Part 4
408 - 1956-06-08 - The Indestructible Mike Matter, Part 5
409 - 1956-06-11 - The Laughing Matter, Part 1
410 - 1956-06-12 - The Laughing Matter, Part 2
411 - 1956-06-13 - The Laughing Matter, Part 3
412 - 1956-06-14 - The Laughing Matter, Part 4
413 - 1956-06-15 - The Laughing Matter, Part 5
414 - 1956-06-18 - The Pearling Matter, Part 1
415 - 1956-06-19 - The Pearling Matter, Part 2
416 - 1956-06-20 - The Pearling Matter, Part 3
417 - 1956-06-21 - The Pearling Matter, Part 4
418 - 1956-06-22 - The Pearling Matter, Part 5
419 - 1956-06-25 - The Long Shot Matter, Part 1
420 - 1956-06-26 - The Long Shot Matter, Part 2
421 - 1956-06-27 - The Long Shot Matter, Part 3
422 - 1956-06-28 - The Long Shot Matter, Part 4
423 - 1956-06-29 - The Long Shot Matter, Part 5
424 - 1956-07-02 - The Midas Touch Matter, Part 1
425 - 1956-07-03 - The Midas Touch Matter, Part 2
426 - 1956-07-04 - The Midas Touch Matter, Part 3
427 - 1956-07-05 - The Midas Touch Matter, Part 4
428 - 1956-07-06 - The Midas Touch Matter, Part 5
429 - 1956-07-09 - The Shady Lane Matter, Part 1
430 - 1956-07-10 - The Shady Lane Matter, Part 2
431 - 1956-07-11 - The Shady Lane Matter, Part 3
432 - 1956-07-12 - The Shady Lane Matter, Part 4
433 - 1956-07-13 - The Shady Lane Matter, Part 5
434 - 1956-07-16 - The Star Of Capetown Matter, Part 1
435 - 1956-07-17 - The Star Of Capetown Matter, Part 2
436 - 1956-07-18 - The Star Of Capetown Matter, Part 3
437 - 1956-07-19 - The Star Of Capetown Matter, Part 4
438 - 1956-07-20 - The Star Of Capetown Matter, Part 5
439 - 1956-07-23 - The Open Town Matter, Part 1
440 - 1956-07-24 - The Open Town Matter, Part 2
441 - 1956-07-25 - The Open Town Matter, Part 3
442 - 1956-07-26 - The Open Town Matter, Part 4
443 - 1956-07-27 - The Open Town Matter, Part 5
444 - 1956-07-30 - The Sea Legs Matter, Part 1
445 - 1956-07-31 - The Sea Legs Matter, Part 2
446 - 1956-08-01 - The Sea Legs Matter, Part 3
447 - 1956-08-02 - The Sea Legs Matter, Part 4
448 - 1956-08-03 - The Sea Legs Matter, Part 5
449 - 1956-08-06 - The Alder Matter, Part 1
450 - 1956-08-07 - The Alder Matter, Part 2
451 - 1956-08-08 - The Alder Matter, Part 3
452 - 1956-08-09 - The Alder Matter, Part 4
453 - 1956-08-10 - The Alder Matter, Part 5
454 - 1956-08-13 - The Crystal Lake Matter, Part 1
455 - 1956-08-14 - The Crystal Lake Matter, Part 2
456 - 1956-08-15 - The Crystal Lake Matter, Part 3
457 - 1956-08-16 - The Crystal Lake Matter, Part 4
458 - 1956-08-17 - The Crystal Lake Matter, Part 5
459 - 1956-08-24 - The Kranesburg Matter, Part 1
460 - 1956-08-27 - The Kranesburg Matter, Part 2
461 - 1956-08-28 - The Kranesburg Matter, Part 3
462 - 1956-08-29 - The Kranesburg Matter, Part 4
463 - 1956-08-30 - The Kranesburg Matter, Part 5
464 - 1956-08-31 - The Kranesburg Matter, Part 6
465 - 1956-09-03 - The Curse Of Kamashek Matter, Part 1
466 - 1956-09-04 - The Curse Of Kamashek Matter, Part 2
467 - 1956-09-05 - The Curse Of Kamashek Matter, Part 3
468 - 1956-09-06 - The Curse Of Kamashek Matter, Part 4
469 - 1956-09-07 - The Curse Of Kamashek Matter, Part 5
470 - 1956-09-10 - The Confidential Matter, Part 1
471 - 1956-09-11 - The Confidential Matter, Part 2
472 - 1956-09-12 - The Confidential Matter, Part 3
473 - 1956-09-13 - The Confidential Matter, Part 4
474 - 1956-09-14 - The Confidential Matter, Part 5
475 - 1956-09-17 - The Imperfect Alibi Matter, Part 1
476 - 1956-09-18 - The Imperfect Alibi Matter, Part 2
477 - 1956-09-19 - The Imperfect Alibi Matter, Part 3
478 - 1956-09-20 - The Imperfect Alibi Matter, Part 4
479 - 1956-09-21 - The Imperfect Alibi Matter, Part 5
480 - 1956-09-24 - The Meg's Palace Matter, Part 1
481 - 1956-09-25 - The Meg's Palace Matter, Part 2
482 - 1956-09-26 - The Meg's Palace Matter, Part 3
483 - 1956-09-27 - The Meg's Palace Matter, Part 4
484 - 1956-09-28 - The Meg's Palace Matter, Part 5
485 - 1956-10-01 - The Picture Postcard Matter, Part 1
486 - 1956-10-02 - The Picture Postcard Matter, Part 2
487 - 1956-10-03 - The Picture Postcard Matter, Part 3
488 - 1956-10-04 - The Picture Postcard Matter, Part 4
489 - 1956-10-05 - The Picture Postcard Matter, Part 5
490 - 1956-10-08 - The Primrose Matter, Part 1
491 - 1956-10-09 - The Primrose Matter, Part 2
492 - 1956-10-10 - The Primrose Matter, Part 3
493 - 1956-10-11 - The Primrose Matter, Part 4
494 - 1956-10-12 - The Primrose Matter, Part 5
495 - 1956-10-15 - The Phantom Chase Matter, Part 1
496 - 1956-10-16 - The Phantom Chase Matter, Part 2
497 - 1956-10-17 - The Phantom Chase Matter, Part 3
498 - 1956-10-18 - The Phantom Chase Matter, Part 4
499 - 1956-10-19 - The Phantom Chase Matter, Part 5
500 - 1956-10-22 - The Phantom Chase Matter, Part 6
501 - 1956-10-24 - The Phantom Chase Matter, Part 7
502 - 1956-10-25 - The Phantom Chase Matter, Part 8
503 - 1956-10-26 - The Phantom Chase Matter, Part 9
504 - 1956-10-29 - The Silent Queen Matter, Part 1
505 - 1956-10-30 - The Silent Queen Matter, Part 2
506 - 1956-10-31 - The Silent Queen Matter, Part 3
507 - 1956-11-01 - The Silent Queen Matter, Part 4
508 - 1956-11-02 - The Silent Queen Matter, Part 5
509 - 1956-11-11 - The Big Scoop Matter
510 - 1956-11-18 - The Markham Matter
511 - 1956-11-25 - The Royal Street Matter
512 - 1956-12-09 - The Burning Carr Matter
513 - 1956-12-16 - The Rasmussen Matter
514 - 1956-12-23 - The Missing Mouse Matter
515 - 1956-12-30 - The Squared Circle Matter
516 - 1957-01-06 - The Ellen Dear Matter
517 - 1957-01-13 - The Desalles Matter
518 - 1957-01-20 - The Blooming Blossom Matter
519 - 1957-01-27 - The Mad Hatter Matter
520 - 1957-02-03 - The Kirbey Will Matter
521 - 1957-02-10 - The Templeton Matter
522 - 1957-02-17 - The Golden Touch Matter
523 - 1957-03-03 - The Meek Memorial Matter
524 - 1957-03-10 - The Suntan Oil Matter
525 - 1957-03-17 - The Clever Chemist Matter
526 - 1957-03-24 - The Hollywood Matter
527 - 1957-03-31 - The Moonshine Murder Matter
528 - 1957-04-14 - The Ming Toy Murphy Matter
529 - 1957-04-21 - The Marley K. Matter
530 - 1957-04-28 - The Melancholy Memory Matter
531 - 1957-05-05 - The Peerless Fire Matter
532 - 1957-05-12 - The Glacier Ghost Matter
533 - 1957-05-19 - The Michael Meany Mirage Matter
534 - 1957-05-26 - The Wayward Truck Matter
535 - 1957-06-02 - The Loss Of Memory Matter
536 - 1957-06-09 - The Mason-Dixon Mismatch Matter
537 - 1957-06-16 - The Dixon Murder Matter
538 - 1957-06-23 - The Parley Barron Matter
539 - 1957-06-30 - The Funny Money Matter
540 - 1957-07-07 - The Felicity Feline Matter
541 - 1957-07-14 - The Heatherstone Players Matter
542 - 1957-07-21 - The Yours Truly Matter
543 - 1957-07-28 - The Confederate Coinage Matter
544 - 1957-08-04 - The Wayward Widow Matter
545 - 1957-08-11 - The Killer's Brand Matter
546 - 1957-08-18 - The Winnipesaukee Wonder Matter
547 - 1957-08-25 - The Smoky Sleeper Matter
548 - 1957-09-01 - The Poor Little Rich Girl Matter
549 - 1957-09-08 - The Charmona Matter
550 - 1957-09-15 - The J. P. D. Matter
551 - 1957-09-22 - The Ideal Vacation Matter
552 - 1957-09-29 - The Doubtful Dairy Matter
553 - 1957-10-06 - The Bum Steer Matter
554 - 1957-10-13 - The Silver Belle Matter
555 - 1957-10-20 - The Mary Grace Matter
556 - 1957-10-27 - The Three Sisters Matter
557 - 1957-11-03 - The Model Picture Matter
558 - 1957-11-10 - The Alkali Mike Matter
559 - 1957-11-17 - The Shy Beneficiary Matter
560 - 1957-11-24 - The Hope To Die Matter
561 - 1957-12-01 - The Sunny Dream Matter
562 - 1957-12-08 - The Hapless Hunter Matter
563 - 1957-12-15 - The Happy Family Matter
564 - 1957-12-22 - The Carmen Kringle Matter
565 - 1957-12-29 - The Latin Lovely Matter
566 - 1958-01-05 - The Ingenuous Jeweler Matter
567 - 1958-01-12 - The Boron 112 Matter
568 - 1958-01-19 - The Eleven O'Clock Matter
569 - 1958-01-26 - The Fire In Paradise Matter
570 - 1958-02-02 - The Price Of Fame Matter
571 - 1958-02-09 - The Sick Chick Matter
572 - 1958-02-16 - The Time And Tide Matter
573 - 1958-02-23 - The Durango Laramie Matter
574 - 1958-03-02 - The Diamond Dilemma Matter
575 - 1958-03-09 - The Wayward Moth Matter
576 - 1958-03-16 - The Salkoff Sequel Matter
577 - 1958-03-23 - The Denver Disbursal Matter
578 - 1958-03-30 - The Killer's List Matter
579 - 1958-04-06 - The Eastern Western Matter
580 - 1958-04-13 - The Wayward Money Matter
581 - 1958-04-20 - The Wayward Trout Matter
582 - 1958-04-27 - The Village Of Virtue Matter
583 - 1958-05-04 - The Carson Arson Matter
584 - 1958-05-11 - The Rolling Stone Matter
585 - 1958-05-18 - The Ghost To Ghost Matter
586 - 1958-05-25 - The Midnite Sun Matter
587 - 1958-06-01 - The Froward Fisherman Matter
588 - 1958-06-08 - The Wayward River Matter
589 - 1958-06-15 - The Delectable Damsel Matter
590 - 1958-06-22 - The Virtuous Mobster Matter
591 - 1958-06-29 - The Ugly Pattern Matter
592 - 1958-07-06 - The Blinker Matter
593 - 1958-07-13 - The Mohave Red Matter
594 - 1958-07-20 - The Mohave Red Sequel Matter
595 - 1958-07-27 - The Wayward Killer Matter
596 - 1958-08-03 - The Lucky 4 Matter
597 - 1958-08-10 - The Two Faced Matter
598 - 1958-08-24 - The Noxious Needle Matter
599 - 1958-08-31 - The Limping Liability Matter
600 - 1958-09-07 - The Malibu Mystery Matter
601 - 1958-09-14 - The Wayward Diamonds Matter
602 - 1958-09-21 - The Johnson Payroll Matter
603 - 1958-09-28 - The Gruesome Spectacle Matter
604 - 1958-10-05 - The Missing Matter Matter
605 - 1958-10-12 - The Impossible Murder Matter
606 - 1958-10-19 - The Monoxide Mystery Matter
607 - 1958-10-26 - The Basking Ridge Matter
608 - 1958-11-02 - The Crater Lake Matter
609 - 1958-11-09 - The Close Shave Matter
610 - 1958-11-16 - The Double Trouble Matter
611 - 1958-11-23 - The One Most Wanted Matter
612 - 1958-11-30 - The Hair Raising Matter
613 - 1958-12-07 - The Perilous Parley Matter
614 - 1958-12-14 - The Allanmee Matter
615 - 1958-12-28 - The Telltale Tracks Matter
616 - 1959-01-04 - The Hollywood Mystery Matter
617 - 1959-01-11 - The Deadly Doubt Matter
618 - 1959-01-18 - The Love Shorn Matter
619 - 1959-01-25 - The Doting Dowager Matter
620 - 1959-02-01 - The Curley Waters Matter
621 - 1959-02-08 - The Date With Death Matter
622 - 1959-02-15 - The Shankar Diamond Matter
623 - 1959-02-22 - The Blue Madonna Matter
624 - 1959-03-01 - The Clouded Crystal Matter
625 - 1959-03-08 - The Net Of Circumstance Matter
626 - 1959-03-15 - The Baldero Matter
627 - 1959-03-22 - The Lake Mead Mystery Matter
628 - 1959-03-29 - The Jimmy Carter Matter
629 - 1959-04-05 - The Frisco Fire Matter
630 - 1959-04-12 - The Fairweather Friend Matter
631 - 1959-04-19 - The Cautious Celibate Matter
632 - 1959-04-26 - The Winsome Widow Matter
633 - 1959-05-03 - The Negligent Nephew Matter
634 - 1959-05-10 - The Fatal Filet Matter
635 - 1959-05-17 - The Twin Trouble Matter
636 - 1959-05-24 - The Casque Of Death Matter
637 - 1959-05-31 - The Big H Matter
638 - 1959-06-07 - The Wayward Heiress Matter
639 - 1959-06-14 - The Wayward Sculptor Matter
640 - 1959-06-21 - The Life At Steak Matter
641 - 1959-06-28 - The Mei-Ling Buddah Matter
642 - 1959-07-05 - The Only One Butt Matter
643 - 1959-07-12 - The Frantic Fisherman Matter
644 - 1959-07-19 - The Will And A Way Matter
645 - 1959-07-26 - The Bolt Out Of The Blue Matter
646 - 1959-08-02 - The Deadly Chain Matter
647 - 1959-08-09 - The Lost By A Hair Matter
648 - 1959-08-16 - The Night In Paris Matter
649 - 1959-08-23 - The Embarcadero Matter
650 - 1959-08-30 - The Really Gone Matter
651 - 1959-09-06 - The Backfire That Backfired Matter
652 - 1959-09-13 - The Leumas Matter
653 - 1959-09-20 - The Little Man Who Was There Matter
654 - 1959-10-04 - The Buffalo Matter
655 - 1959-10-11 - The Further Buffalo Matter
656 - 1959-10-18 - The Double Identity Matter
657 - 1959-10-25 - The Missing Missile Matter
658 - 1959-11-01 - The Hand Of Providential Matter
659 - 1959-11-08 - The Larson Arson Matter
660 - 1959-11-15 - The Bayou Body Matter
661 - 1959-11-22 - The Fancy Bridgework Matter
662 - 1959-11-29 - The Wrong Man Matter
663 - 1959-12-06 - The Hired Homicide Matter
664 - 1959-12-13 - The Sudden Wealth Matter
665 - 1959-12-20 - The Red Mystery Matter
666 - 1959-12-27 - The Burning Desire Matter
667 - 1960-01-03 - The Hapless Ham Matter
668 - 1960-01-10 - The Unholy Two Matter
669 - 1960-01-17 - The Evaporated Clue Matter
670 - 1960-01-24 - The Nuclear Goof Matter
671 - 1960-01-31 - The Merry Go Round Matter
672 - 1960-02-07 - The Sidewinder Matter
673 - 1960-02-14 - The P. O. Matter
674 - 1960-02-21 - The Alvin's Alfred Matter
675 - 1960-02-28 - The Look Before The Leap Matter
676 - 1960-03-06 - The Moonshine Matter
677 - 1960-03-13 - The Deep Down Matter
678 - 1960-03-20 - The Saturday Night Matter
679 - 1960-03-27 - The False Alarm Matter
680 - 1960-04-03 - The Double Exposure Matter
681 - 1960-04-17 - The Deadly Swamp Matter
682 - 1960-04-24 - The Silver Queen Matter
683 - 1960-05-01 - The Fatal Switch Matter
684 - 1960-05-08 - The Phony Phone Matter
685 - 1960-05-15 - The Mystery Gal Matter
686 - 1960-05-22 - The Man Who Waits Matter
687 - 1960-05-29 - The Redrock Matter
688 - 1960-06-05 - The Canned Canary Matter
689 - 1960-06-12 - The Harried Heiress Matter
690 - 1960-06-19 - The Flask Of Death Matter
691 - 1960-06-26 - The Wholly Unexpected Matter
692 - 1960-07-03 - The Collector's Matter
693 - 1960-07-17 - The Back To The Back Matter
694 - 1960-07-31 - The Rhymer Collection Matter
695 - 1960-08-07 - The Magnanimous Matter
696 - 1960-08-14 - The Paradise Lost Matter
697 - 1960-08-21 - The Twisted Twin Matter
698 - 1960-08-28 - The Deadly Debt Matter
699 - 1960-09-04 - The Killer Kin Matter
700 - 1960-09-11 - The Too Much Money Matter
701 - 1960-09-18 - The Real Smokey Matter
702 - 1960-09-25 - The Five Down Matter
703 - 1960-10-02 - The Stope Of Death Matter
704 - 1960-10-09 - The Recompense Matter
705 - 1960-10-16 - The Twins Of Tahoe Matter
706 - 1960-10-23 - The Unworthy Kin Matter
707 - 1960-10-30 - The What Goes Matter
708 - 1960-11-06 - The Super Salesman Matter
709 - 1960-11-13 - The Bad One Matter
710 - 1960-11-20 - The Double Deal Matter
711 - 1960-11-27 - The Empty Threat Matter
712 - 1960-12-04 - The Urned Income Matter
713 - 1960-12-11 - The Wrong Ending Matter aka The Locked Room Murder Matter
714 - 1960-12-18 - The Wayward Kilocycles Matter
715 - 1960-12-25 - The Art For My Sake Matter aka The Christmas Present Matter
716 - 1961-01-01 - The True Love Matter aka The Missing Jewels Matter
717 - 1961-01-08 - The Big Date Matter
718 - 1961-01-15 - The Very Fishy Matter
719 - 1961-01-22 - The Short Term Matter aka The Dollar Put In Jail Matter
720 - 1961-01-29 - The Death By Jet Matter aka The Paperback Mystery Matter
721 - 1961-02-05 - The Planner Matter
722 - 1961-02-12 - The Who's Who Matter
723 - 1961-02-19 - The Wayward Fireman Matter
724 - 1961-02-26 - The Two Tired Matter
725 - 1961-03-05 - The Touch-Up Matter
726 - 1961-03-12 - The Morning After Matter
727 - 1961-03-19 - The Ring Of Death Matter
728 - 1961-03-26 - The Informer Matter
729 - 1961-04-02 - The Two's A Crowd Matter
730 - 1961-04-09 - The Wrong Sign Matter
731 - 1961-04-16 - The Captain's Table Matter
732 - 1961-04-23 - The Latrodectus Matter
732 - 1961-04-30 - The Rat Pack Matter
732 - 1961-05-07 - The Purple Doll Matter
735 - 1961-05-14 - The Newark Stockbroker Matter
736 - 1961-05-21 - The Simple Simon Matter
737 - 1961-05-28 - The Lone Wolf Matter
738 - 1961-06-04 - The Yaak Mystery Matter
739 - 1961-06-11 - The Stock-In-Trade Matter
740 - 1961-06-18 - The Million Dollar Matter
741 - 1961-06-25 - The Low Tide Matter
742 - 1961-07-02 - The Imperfect Crime Matter
743 - 1961-07-09 - The Well Of Trouble Matter
744 - 1961-07-16 - The Fiddle Faddle Matter
745 - 1961-07-23 - The Old Fashioned Murder Matter
746 - 1961-07-30 - The Chuckanut Matter
747 - 1961-08-06 - The Philadelphia Miss Matter
748 - 1961-08-13 - The Perilous Padre Matter
749 - 1961-08-20 - The Wrong Doctor Matter
750 - 1961-08-27 - Too Many Crooks Matter
751 - 1961-09-03 - The Shifty Looker Matter
752 - 1961-09-10 - The All Wet Matter
752 - 1961-09-17 - The Buyer And The Cellar Matter
754 - 1961-09-24 - The Clever Crook Matter
754 - 1961-10-01 - The Double-Barreled Matter
756 - 1961-10-08 - The Medium Rare Matter
757 - 1961-10-15 - The Quiet Little Town In New Jersey Matter
758 - 1961-10-22 - The Three For One Matter
759 - 1961-10-29 - The Bee Or Not To Bee Matter
760 - 1961-11-05 - The Monticello Mystery Matter
761 - 1961-11-12 - The Wrong One Matter
762 - 1961-11-19 - The Guide To Murder Matter
763 - 1961-11-26 - The Mad Bomber Matter
764 - 1961-12-03 - The Cinder Elmer Matter
765 - 1961-12-10 - The Firebug Matter
766 - 1961-12-17 - The Phony Phone Matter
767 - 1961-12-31 - The One Too Many Matter
768 - 1962-01-07 - The Hot Chocolate Matter
769 - 1962-01-14 - The Gold Rush Country Matter
770 - 1962-01-21 - The Terrible Torch Matter
771 - 1962-01-28 - The Can't Be So Matter
772 - 1962-02-04 - The Nugget Of Truth Matter
773 - 1962-02-11 - The Do It Yourself Matter
774 - 1962-02-18 - The Takes A Crook Matter
775 - 1962-02-25 - The Mixed Blessing Matter
776 - 1962-03-04 - The Top Secret Matter
777 - 1962-03-11 - The Golden Dream Matter
778 - 1962-03-18 - The Ike And Mike Matter
779 - 1962-03-25 - The Shadow Of A Doubt Matter
780 - 1962-04-01 - The Blue Rock Matter
781 - 1962-04-08 - The Ivy Emerald Matter
782 - 1962-04-15 - The Wrong Idea Matter
783 - 1962-04-22 - The Skidmore Matter
784 - 1962-04-29 - The Grand Canyon Matter
785 - 1962-05-06 - The Burma Red Matter
786 - 1962-05-13 - The Lust For Gold Matter
787 - 1962-05-20 - The Two Steps To Murder Matter
788 - 1962-05-27 - The Zipp Matter
789 - 1962-06-03 - The Wayward Gun Matter
790 - 1962-06-10 - The Wayward Clipper Matter aka The Tuna Clipper Matter
791 - 1962-06-17 - The All Too Easy Matter
792 - 1962-06-24 - The Hood Of Death Matter
793 - 1962-07-01 - The Vociferous Dolphin Matter
794 - 1962-07-08 - The Rilldo Matter
795 - 1962-07-15 - The Weather Or Not Matter
796 - 1962-07-22 - The Skimpy Matter
797 - 1962-07-29 - The Four's A Crowd Matter
798 - 1962-08-05 - The Case Of Trouble Matter
799 - 1962-08-12 - The Oldest Gag Matter
800 - 1962-08-19 - The Lorelei Matter
801 - 1962-08-26 - The Gold Rush Matter
802 - 1962-09-02 - The Doninger Doninger Matter
803 - 1962-09-09 - The Four Cs Matter
804 - 1962-09-16 - The No Matter Matter
805 - 1962-09-23 - The Deadly Crystal Matter
806 - 1962-09-30 - The Tip-Off Matter
""".strip().split("\n")

best_lines = """
Yours Truly, Johnny Dollar - 1948-12-07 - 000 - Milford Brooks III.flac | 1
Yours Truly, Johnny Dollar - 1949-02-18 - 001 - The Parakoff Policy.flac | 2
Yours Truly, Johnny Dollar - 1949-02-25 - 002 - The Slow Boat From China.mp3 | 3
Yours Truly, Johnny Dollar - 1949-03-04 - 003 - The Robert Perry Case.flac | 4
Yours Truly, Johnny Dollar - 1949-03-11 - 004 - Murder Is A Merry-Go-Round.mp3 | 5
Yours Truly, Johnny Dollar - 1949-03-25 - 005 - Milford Brooks III Matter.flac | 6
Yours Truly, Johnny Dollar - 1949-04-01 - 006 - The Stolen Portrait Of The Duke Of Massen.flac | 7
Yours Truly, Johnny Dollar - 1949-04-15 - 008 - The Case Of The Hundred Thousand Dollar Legs.mp3 | 9
Yours Truly, Johnny Dollar - 1949-04-22 - 009 - The Case Of Barton Drake.flac | 10
Yours Truly, Johnny Dollar - 1949-07-24 - 011 - Who Took The Taxis For A Ride.flac | 12
Yours Truly, Johnny Dollar - 1949-08-07 - 013 - Murder Ain't Minor.mp3 | 14
Yours Truly, Johnny Dollar - 1949-08-21 - 015 - Out Of The Fire, Into The Frying Pan.flac | 16
Yours Truly, Johnny Dollar - 1949-09-04 - 017 - The Expiring Nickels And The Egyptian Jackpot.mp3 | 18
Yours Truly, Johnny Dollar - 1949-09-25 - 018 - The Search For Michelle Marsh.flac | 19
Yours Truly, Johnny Dollar - 1949-10-01 - 019 - The Fishing Boat Affair.flac | 20
Yours Truly, Johnny Dollar - 1949-10-08 - 020 - The Racehorse Piledriver Matter.mp3 | 21
Yours Truly, Johnny Dollar - 1949-10-15 - 021 - Dr. Otto Schmedlich.mp3 | 22
Yours Truly, Johnny Dollar - 1949-10-22 - 022 - Witness, Witness, Who's Got The Witness.mp3 | 23
Yours Truly, Johnny Dollar - 1949-10-29 - 023 - The Little Man Who Wasn't All There.mp3 | 24
Yours Truly, Johnny Dollar - 1949-11-05 - 024 - The Island Of Tin-Yutan.mp3 | 25
Yours Truly, Johnny Dollar - 1949-11-12 - 025 - The Melanie Carter Matter.mp3 | 26
Yours Truly, Johnny Dollar - 1949-11-26 - 026 - The Skull Canyon Mine.flac | 27
Yours Truly, Johnny Dollar - 1949-12-03 - 027 - Bodyguard To Anne Connelly.flac | 28
Yours Truly, Johnny Dollar - 1949-12-10 - 028 - The Circus Animal Show Matter.mp3 | 29
Yours Truly, Johnny Dollar - 1949-12-17 - 029 - Haiti Adventure Matter.flac | 30
Yours Truly, Johnny Dollar - 1949-12-24 - 030 - How I Played Santa Claus And Almost Got Left Holding The Bag.flac | 31
Yours Truly, Johnny Dollar - 1950-02-03 - 034 - Death Takes A Working Day.mp3 | 35
Yours Truly, Johnny Dollar - 1950-02-10 - 035 - The S.S. Malay Trader Ship.mp3 | 36
Yours Truly, Johnny Dollar - 1950-02-17 - 036 - The Gravedigger's Spades.mp3 | 37
Yours Truly, Johnny Dollar - 1950-02-24 - 037 - The Archeologist.mp3 | 38
Yours Truly, Johnny Dollar - 1950-03-03 - 038 - Bodyguard To The Late Robert W. Perry.mp3 | 39
Yours Truly, Johnny Dollar - 1950-03-07 - 039 - Alec Jefferson, The Youthful Millionaire.mp3 | 40
Yours Truly, Johnny Dollar - 1950-03-14 - 040 - The Eighty-Five Little Minks.mp3 | 41
Yours Truly, Johnny Dollar - 1950-03-21 - 041 - The Man Who Wrote Himself To Death.mp3 | 42
Yours Truly, Johnny Dollar - 1950-03-28 - 042 - The Village Scene Matter.mp3 | 43
Yours Truly, Johnny Dollar - 1950-04-04 - 043 - The Story Of The Big Red Schoolhouse.mp3 | 44
Yours Truly, Johnny Dollar - 1950-04-11 - 044 - The Dead First-Helpers.flac | 45
Yours Truly, Johnny Dollar - 1950-04-18 - 045 - The Story Of The Ten-O-Eight.mp3 | 46
Yours Truly, Johnny Dollar - 1950-04-25 - 046 - Pearl Carrasa.mp3 | 47
Yours Truly, Johnny Dollar - 1950-05-02 - 047 - The Able Tackitt Matter.mp3 | 48
Yours Truly, Johnny Dollar - 1950-05-09 - 048 - The Harold Trandem Matter.mp3 | 49
Yours Truly, Johnny Dollar - 1950-05-16 - 049 - The Sidney Rykoff Matter.mp3 | 50
Yours Truly, Johnny Dollar - 1950-05-23 - 050 - The Earl Chadwick Matter.mp3 | 51
Yours Truly, Johnny Dollar - 1950-05-30 - 051 - The Port-au-Prince Matter.mp3 | 52
Yours Truly, Johnny Dollar - 1950-06-08 - 052 - The Caligio Diamond Matter.mp3 | 53
Yours Truly, Johnny Dollar - 1950-06-15 - 053 - The Arrowcraft Matter.flac | 54
Yours Truly, Johnny Dollar - 1950-06-22 - 054 - The London Matter.mp3 | 55
Yours Truly, Johnny Dollar - 1950-06-29 - 055 - The Barbara James Matter.mp3 | 56
Yours Truly, Johnny Dollar - 1950-07-06 - 056 - The Belo-Horizonte Railroad.mp3 | 57
Yours Truly, Johnny Dollar - 1950-07-13 - 057 - The Calgary Matter.mp3 | 58
Yours Truly, Johnny Dollar - 1950-07-20 - 058 - The Henry J. Unger Matter.mp3 | 59
Yours Truly, Johnny Dollar - 1950-08-03 - 060 - The Blood River Matter.mp3 | 61
Yours Truly, Johnny Dollar - 1950-08-10 - 061 - The Hartford Alliance Matter.mp3 | 62
Yours Truly, Johnny Dollar - 1950-08-17 - 062 - The Mickey McQueen Matter.mp3 | 63
Yours Truly, Johnny Dollar - 1950-08-24 - 063 - The Trans-Pacific Import Export Company, South China Branch Matter.mp3 | 64
Yours Truly, Johnny Dollar - 1950-08-31 - 064 - The Virginia Beach Matter.mp3 | 65
Yours Truly, Johnny Dollar - 1950-09-30 - 065 - The Howard Caldwell Matter.mp3 | 66
Yours Truly, Johnny Dollar - 1950-10-07 - 066 - The Richard Splain Matter.mp3 | 67
Yours Truly, Johnny Dollar - 1950-10-14 - 067 - The Yankee Pride Matter.flac | 68
Yours Truly, Johnny Dollar - 1950-10-21 - 068 - The Jack Madigan Matter.mp3 | 69
Yours Truly, Johnny Dollar - 1950-10-28 - 069 - The Joan Sebastian Matter.mp3 | 70
Yours Truly, Johnny Dollar - 1950-11-04 - 070 - The Queen Anne Pistols Matter.mp3 | 71
Yours Truly, Johnny Dollar - 1950-11-11 - 071 - The Adam Kegg Matter.mp3 | 72
Yours Truly, Johnny Dollar - 1950-11-18 - 072 - The Nora Faulkner Matter.flac | 73
Yours Truly, Johnny Dollar - 1950-11-25 - 073 - The Woodward Manila Matter.mp3 | 74
Yours Truly, Johnny Dollar - 1950-12-16 - 074 - The Leland Blackburn Matter (Rehearsal).flac | 75
Yours Truly, Johnny Dollar - 1951-01-13 - 078 - The Port-O-Call Matter.mp3 | 79
Yours Truly, Johnny Dollar - 1951-01-20 - 079 - The David Rockey Matter.mp3 | 80
Yours Truly, Johnny Dollar - 1951-02-24 - 084 - The Jarvis Wilder Matter.mp3 | 85
Yours Truly, Johnny Dollar - 1951-03-03 - 085 - The Celia Woodstock Matter.mp3 | 86
Yours Truly, Johnny Dollar - 1951-03-10 - 086 - The Stanley Springs Matter.mp3 | 87
Yours Truly, Johnny Dollar - 1951-03-24 - 088 - The Byron Hayes Matter.mp3 | 89
Yours Truly, Johnny Dollar - 1951-03-31 - 089 - The Jackie Cleaver Matter.mp3 | 90
Yours Truly, Johnny Dollar - 1951-04-07 - 090 - The Edward French Matter.mp3 | 91
Yours Truly, Johnny Dollar - 1951-04-14 - 091 - The Mickey McQueen Matter.mp3 | 92
Yours Truly, Johnny Dollar - 1951-04-21 - 092 - The Willard South Matter.mp3 | 93
Yours Truly, Johnny Dollar - 1951-04-28 - 093 - The Month-End Raid Matter.mp3 | 94
Yours Truly, Johnny Dollar - 1951-05-05 - 094 - The Virginia Towne Matter.flac | 95
Yours Truly, Johnny Dollar - 1951-05-26 - 097 - The Lillis Bond Matter.mp3 | 98
Yours Truly, Johnny Dollar - 1951-06-02 - 098 - The Soderbury, Maine Matter.mp3 | 99
Yours Truly, Johnny Dollar - 1951-06-09 - 099 - The George Farmer Matter.mp3 | 100
Yours Truly, Johnny Dollar - 1951-06-16 - 100 - The Arthur Boldrick Matter.mp3 | 101
Yours Truly, Johnny Dollar - 1951-06-20 - 101 - The Malcolm Wish M.D. Matter.mp3 | 102
Yours Truly, Johnny Dollar - 1951-06-27 - 102 - The Hatchet House Theft Matter.mp3 | 103
Yours Truly, Johnny Dollar - 1951-07-04 - 103 - The Alonzo Chapman Matter.mp3 | 104
Yours Truly, Johnny Dollar - 1951-07-11 - 104 - The Fair-Way Matter.mp3 | 105
Yours Truly, Johnny Dollar - 1951-07-18 - 105 - The Neal Breer Matter.mp3 | 106
Yours Truly, Johnny Dollar - 1951-08-01 - 107 - The Horace Lockhart Matter.mp3 | 108
Yours Truly, Johnny Dollar - 1951-08-15 - 109 - The Lucky Costa Matter.flac | 110
Yours Truly, Johnny Dollar - 1951-08-29 - 111 - The Leland Case Matter.mp3 | 112
Yours Truly, Johnny Dollar - 1951-09-19 - 113 - The Cuban Jewel Matter.flac | 114
Yours Truly, Johnny Dollar - 1951-09-26 - 114 - The Protection Matter.mp3 | 115
Yours Truly, Johnny Dollar - 1951-10-06 - 115 - The Douglas Taylor Matter.mp3 | 116
Yours Truly, Johnny Dollar - 1951-10-13 - 116 - The Millard Ward Matter.mp3 | 117
Yours Truly, Johnny Dollar - 1951-10-27 - 118 - The Tolhurst Theft Matter.mp3 | 119
Yours Truly, Johnny Dollar - 1951-11-03 - 119 - The Hannibal Murphy Matter.flac | 120
Yours Truly, Johnny Dollar - 1951-11-10 - 120 - The Birdy Baskerville Matter.mp3 | 121
Yours Truly, Johnny Dollar - 1951-11-17 - 121 - The Merrill Kent Matter.mp3 | 122
Yours Truly, Johnny Dollar - 1951-12-08 - 122 - The Youngstown Credit Group Matter.mp3 | 123
Yours Truly, Johnny Dollar - 1951-12-22 - 124 - The Maynard Collins Matter.mp3 | 125
Yours Truly, Johnny Dollar - 1951-12-29 - 125 - The Alma Scott Matter.mp3 | 126
Yours Truly, Johnny Dollar - 1952-01-05 - 126 - The Glen English Matter.mp3 | 127
Yours Truly, Johnny Dollar - 1952-07-02 - 128 - The Amelia Harwell Matter.mp3 | 129
Yours Truly, Johnny Dollar - 1952-11-24 - 000 - The Trans-Pacific Matter, Part 1.mp3 | 137
Yours Truly, Johnny Dollar - 1952-11-28 - 000 - The Trans-Pacific Matter, Part 2.mp3 | 138
Yours Truly, Johnny Dollar - 1952-12-05 - 139 - The James Clayton Matter.flac | 140
Yours Truly, Johnny Dollar - 1952-12-12 - 140 - The Elliott Champion Matter.mp3 | 141
Yours Truly, Johnny Dollar - 1952-12-26 - 142 - The Walter Patterson Matter.flac | 143
Yours Truly, Johnny Dollar - 1953-01-02 - 143 - The Baltimore Matter.flac | 144
Yours Truly, Johnny Dollar - 1953-01-09 - 144 - The Thelma Ibsen Matter.mp3 | 145
Yours Truly, Johnny Dollar - 1953-01-16 - 145 - The Starlet Matter.mp3 | 146
Yours Truly, Johnny Dollar - 1953-01-23 - 146 - The Marigold Matter.mp3 | 147
Yours Truly, Johnny Dollar - 1953-01-30 - 147 - The Kay Bellamy Matter.flac | 148
Yours Truly, Johnny Dollar - 1953-02-06 - 148 - The Chicago Fraud Matter.flac | 149
Yours Truly, Johnny Dollar - 1953-02-20 - 150 - The Latourette Matter.mp3 | 151
Yours Truly, Johnny Dollar - 1953-02-27 - 151 - The Underwood Matter.mp3 | 152
Yours Truly, Johnny Dollar - 1953-03-06 - 152 - The Jeanne Maxwell Matter.mp3 | 153
Yours Truly, Johnny Dollar - 1953-03-17 - 154 - The King's Necklace Matter.mp3 | 155
Yours Truly, Johnny Dollar - 1953-03-24 - 155 - The Syndicate Matter.mp3 | 156
Yours Truly, Johnny Dollar - 1953-03-31 - 156 - The Lester James Matter.flac | 157
Yours Truly, Johnny Dollar - 1953-04-07 - 157 - The Enoch Arden Matter.flac | 158
Yours Truly, Johnny Dollar - 1953-04-14 - 158 - The Madison Matter.mp3 | 159
Yours Truly, Johnny Dollar - 1953-04-21 - 159 - The Dameron Matter.mp3 | 160
Yours Truly, Johnny Dollar - 1953-04-28 - 160 - The San Antonio Matter.mp3 | 161
Yours Truly, Johnny Dollar - 1953-05-05 - 161 - The Blackmail Matter.mp3 | 162
Yours Truly, Johnny Dollar - 1953-05-12 - 162 - The Rochester Theft Matter.mp3 | 163
Yours Truly, Johnny Dollar - 1953-05-19 - 163 - The Emily Braddock Matter.mp3 | 164
Yours Truly, Johnny Dollar - 1953-05-26 - 164 - The Brisbane Fraud Matter.mp3 | 165
Yours Truly, Johnny Dollar - 1953-06-02 - 165 - The Costain Matter.mp3 | 166
Yours Truly, Johnny Dollar - 1953-06-09 - 166 - The Oklahoma Red Matter.mp3 | 167
Yours Truly, Johnny Dollar - 1953-06-16 - 167 - The Emil Carter Matter.mp3 | 168
Yours Truly, Johnny Dollar - 1953-06-23 - 168 - The Jonathan Bellows Matter.mp3 | 169
Yours Truly, Johnny Dollar - 1953-06-30 - 169 - The Jones Matter.mp3 | 170
Yours Truly, Johnny Dollar - 1953-07-14 - 171 - The Shayne Bombing Matter.flac | 172
Yours Truly, Johnny Dollar - 1953-07-21 - 172 - The Black Doll Matter.mp3 | 173
Yours Truly, Johnny Dollar - 1953-07-28 - 173 - The James Forbes Matter.mp3 | 174
Yours Truly, Johnny Dollar - 1953-08-04 - 174 - The Voodoo Matter.mp3 | 175
Yours Truly, Johnny Dollar - 1953-08-11 - 175 - The Nancy Shaw Matter.mp3 | 176
Yours Truly, Johnny Dollar - 1953-08-18 - 176 - The Isabel James Matter.mp3 | 177
Yours Truly, Johnny Dollar - 1953-08-25 - 177 - The Nelson Matter.mp3 | 178
Yours Truly, Johnny Dollar - 1953-09-01 - 178 - The Stanley Price Matter.mp3 | 179
Yours Truly, Johnny Dollar - 1953-09-08 - 179 - The Lester Matson Matter.mp3 | 180
Yours Truly, Johnny Dollar - 1953-09-22 - 181 - The William Post Matter.mp3 | 182
Yours Truly, Johnny Dollar - 1953-09-29 - 182 - The Amita Buddha Matter.mp3 | 183
Yours Truly, Johnny Dollar - 1953-10-06 - 183 - The Alfred Chambers Matter.mp3 | 184
Yours Truly, Johnny Dollar - 1953-10-13 - 184 - The Philip Morey Matter.mp3 | 185
Yours Truly, Johnny Dollar - 1953-10-20 - 185 - The Allen Saxton Matter.mp3 | 186
Yours Truly, Johnny Dollar - 1953-10-27 - 186 - The Howard Arnold Matter.mp3 | 187
Yours Truly, Johnny Dollar - 1953-11-03 - 187 - The Gino Gambona Matter.mp3 | 188
Yours Truly, Johnny Dollar - 1953-11-10 - 188 - The Bobby Foster Matter.mp3 | 189
Yours Truly, Johnny Dollar - 1953-11-17 - 189 - The Nathan Gayles Matter.mp3 | 190
Yours Truly, Johnny Dollar - 1953-11-24 - 190 - The Independent Diamond Traders' Matter.mp3 | 191
Yours Truly, Johnny Dollar - 1953-12-01 - 191 - The Monopoly Matter.mp3 | 192
Yours Truly, Johnny Dollar - 1953-12-08 - 192 - The Barton Baker Matter.mp3 | 193
Yours Truly, Johnny Dollar - 1953-12-15 - 193 - The Milk And Honey Matter.mp3 | 194
Yours Truly, Johnny Dollar - 1953-12-29 - 195 - The Ben Bryson Matter.mp3 | 196
Yours Truly, Johnny Dollar - 1954-01-05 - 196 - The Fair-Way Matter.mp3 | 197
Yours Truly, Johnny Dollar - 1954-01-12 - 197 - The Celia Woodstock Matter.mp3 | 198
Yours Truly, Johnny Dollar - 1954-01-26 - 199 - The Beauregard Matter.mp3 | 200
Yours Truly, Johnny Dollar - 1954-02-02 - 200 - The Paul Gorrell Matter.mp3 | 201
Yours Truly, Johnny Dollar - 1954-02-09 - 201 - The Harpooned Angler Matter.mp3 | 202
Yours Truly, Johnny Dollar - 1954-02-16 - 202 - The Uncut Canary Matter.mp3 | 203
Yours Truly, Johnny Dollar - 1954-02-23 - 203 - The Classified Killer Matter.mp3 | 204
Yours Truly, Johnny Dollar - 1954-03-02 - 204 - The Road-Test Matter.mp3 | 205
Yours Truly, Johnny Dollar - 1954-03-09 - 205 - The Terrified Taun Matter.mp3 | 206
Yours Truly, Johnny Dollar - 1954-03-16 - 206 - The Berlin Matter.mp3 | 207
Yours Truly, Johnny Dollar - 1954-03-23 - 207 - The Piney Corners Matter.mp3 | 208
Yours Truly, Johnny Dollar - 1954-04-06 - 209 - The Sulphur And Brimstone Matter.mp3 | 210
Yours Truly, Johnny Dollar - 1954-04-13 - 210 - The Magnolia And Honeysuckle Matter.mp3 | 211
Yours Truly, Johnny Dollar - 1954-04-20 - 211 - The Nathan Swing Matter.mp3 | 212
Yours Truly, Johnny Dollar - 1954-04-27 - 212 - The Frustrated Phoenix Matter.mp3 | 213
Yours Truly, Johnny Dollar - 1954-05-04 - 213 - The Dan Frank Matter.mp3 | 214
Yours Truly, Johnny Dollar - 1954-05-18 - 215 - The Bilked Baroness Matter.mp3 | 216
Yours Truly, Johnny Dollar - 1954-05-25 - 216 - The Punctilious Firebug Matter.mp3 | 217
Yours Truly, Johnny Dollar - 1954-06-01 - 217 - The Temperamental Tote Board Matter.mp3 | 218
Yours Truly, Johnny Dollar - 1954-06-08 - 218 - The Sara Dearing Matter.mp3 | 219
Yours Truly, Johnny Dollar - 1954-06-15 - 219 - The Paterson Transport Matter.mp3 | 220
Yours Truly, Johnny Dollar - 1954-06-29 - 221 - The Woodward Manila Matter.flac | 222
Yours Truly, Johnny Dollar - 1954-07-06 - 222 - The Jan Brueghel Matter.mp3 | 223
Yours Truly, Johnny Dollar - 1954-07-13 - 223 - The Carboniferous Dolomite Matter.mp3 | 224
Yours Truly, Johnny Dollar - 1954-07-20 - 224 - The Jeanne Maxwell Matter.mp3 | 225
Yours Truly, Johnny Dollar - 1954-07-27 - 225 - The Radioactive Gold Matter.mp3 | 226
Yours Truly, Johnny Dollar - 1954-08-03 - 226 - The Hampton Line Matter.mp3 | 227
Yours Truly, Johnny Dollar - 1955-08-29 - 000 - The Trans-Pacific Import-Export Matter.flac | 232
Yours Truly, Johnny Dollar - 1955-10-03 - 231 - The Macormack Matter, Part 1.flac | 233
Yours Truly, Johnny Dollar - 1955-10-04 - 232 - The Macormack Matter, Part 2.flac | 234
Yours Truly, Johnny Dollar - 1955-10-05 - 233 - The Macormack Matter, Part 3.flac | 235
Yours Truly, Johnny Dollar - 1955-10-06 - 234 - The Macormack Matter, Part 4.flac | 236
Yours Truly, Johnny Dollar - 1955-10-07 - 235 - The Macormack Matter, Part 5.flac | 237
Yours Truly, Johnny Dollar - 1955-10-10 - 236 - The Molly K Matter, Part 1.flac | 238
Yours Truly, Johnny Dollar - 1955-10-11 - 237 - The Molly K Matter, Part 2.flac | 239
Yours Truly, Johnny Dollar - 1955-10-12 - 238 - The Molly K Matter, Part 3.flac | 240
Yours Truly, Johnny Dollar - 1955-10-13 - 239 - The Molly K Matter, Part 4.flac | 241
Yours Truly, Johnny Dollar - 1955-10-14 - 240 - The Molly K Matter, Part 5.flac | 242
Yours Truly, Johnny Dollar - 1955-10-17 - 241 - The Chesapeake Fraud Matter, Part 1.flac | 243
Yours Truly, Johnny Dollar - 1955-10-18 - 242 - The Chesapeake Fraud Matter, Part 2.flac | 244
Yours Truly, Johnny Dollar - 1955-10-19 - 243 - The Chesapeake Fraud Matter, Part 3.flac | 245
Yours Truly, Johnny Dollar - 1955-10-20 - 244 - The Chesapeake Fraud Matter, Part 4.flac | 246
Yours Truly, Johnny Dollar - 1955-10-21 - 245 - The Chesapeake Fraud Matter, Part 5.flac | 247
Yours Truly, Johnny Dollar - 1955-10-24 - 246 - The Alvin Summers Matter, Part 1.flac | 248
Yours Truly, Johnny Dollar - 1955-10-25 - 247 - The Alvin Summers Matter, Part 2.flac | 249
Yours Truly, Johnny Dollar - 1955-10-26 - 248 - The Alvin Summers Matter, Part 3.flac | 250
Yours Truly, Johnny Dollar - 1955-10-27 - 249 - The Alvin Summers Matter, Part 4.flac | 251
Yours Truly, Johnny Dollar - 1955-10-28 - 250 - The Alvin Summers Matter, Part 5.flac | 252
Yours Truly, Johnny Dollar - 1955-10-31 - 251 - The Valentine Matter, Part 1.flac | 253
Yours Truly, Johnny Dollar - 1955-11-01 - 252 - The Valentine Matter, Part 2.flac | 254
Yours Truly, Johnny Dollar - 1955-11-02 - 253 - The Valentine Matter, Part 3.flac | 255
Yours Truly, Johnny Dollar - 1955-11-03 - 254 - The Valentine Matter, Part 4.flac | 256
Yours Truly, Johnny Dollar - 1955-11-04 - 255 - The Valentine Matter, Part 5.flac | 257
Yours Truly, Johnny Dollar - 1955-11-07 - 256 - The Lorko Diamonds Matter, Part 1.flac | 258
Yours Truly, Johnny Dollar - 1955-11-08 - 257 - The Lorko Diamonds Matter, Part 2.flac | 259
Yours Truly, Johnny Dollar - 1955-11-09 - 258 - The Lorko Diamonds Matter, Part 3.flac | 260
Yours Truly, Johnny Dollar - 1955-11-10 - 259 - The Lorko Diamonds Matter, Part 4.flac | 261
Yours Truly, Johnny Dollar - 1955-11-11 - 260 - The Lorko Diamonds Matter, Part 5.flac | 262
Yours Truly, Johnny Dollar - 1955-11-14 - 261 - The Broderick Matter, Part 1.flac | 263
Yours Truly, Johnny Dollar - 1955-11-15 - 262 - The Broderick Matter, Part 2.flac | 264
Yours Truly, Johnny Dollar - 1955-11-16 - 263 - The Broderick Matter, Part 3.flac | 265
Yours Truly, Johnny Dollar - 1955-11-17 - 264 - The Broderick Matter, Part 4.flac | 266
Yours Truly, Johnny Dollar - 1955-11-18 - 265 - The Broderick Matter, Part 5.flac | 267
Yours Truly, Johnny Dollar - 1955-11-21 - 266 - The Amy Bradshaw Matter, Part 1.flac | 268
Yours Truly, Johnny Dollar - 1955-11-22 - 267 - The Amy Bradshaw Matter, Part 2.flac | 269
Yours Truly, Johnny Dollar - 1955-11-23 - 268 - The Amy Bradshaw Matter, Part 3.flac | 270
Yours Truly, Johnny Dollar - 1955-11-24 - 269 - The Amy Bradshaw Matter, Part 4.flac | 271
Yours Truly, Johnny Dollar - 1955-11-25 - 270 - The Amy Bradshaw Matter, Part 5.flac | 272
Yours Truly, Johnny Dollar - 1955-11-28 - 271 - The Henderson Matter, Part 1.flac | 273
Yours Truly, Johnny Dollar - 1955-11-29 - 272 - The Henderson Matter, Part 2.flac | 274
Yours Truly, Johnny Dollar - 1955-11-30 - 273 - The Henderson Matter, Part 3.flac | 275
Yours Truly, Johnny Dollar - 1955-12-01 - 274 - The Henderson Matter, Part 4.flac | 276
Yours Truly, Johnny Dollar - 1955-12-02 - 275 - The Henderson Matter, Part 5.flac | 277
Yours Truly, Johnny Dollar - 1955-12-05 - 276 - The Cronin Matter, Part 1.flac | 278
Yours Truly, Johnny Dollar - 1955-12-06 - 277 - The Cronin Matter, Part 2.flac | 279
Yours Truly, Johnny Dollar - 1955-12-07 - 278 - The Cronin Matter, Part 3.flac | 280
Yours Truly, Johnny Dollar - 1955-12-08 - 279 - The Cronin Matter, Part 4.flac | 281
Yours Truly, Johnny Dollar - 1955-12-09 - 280 - The Cronin Matter, Part 5.flac | 282
Yours Truly, Johnny Dollar - 1955-12-12 - 281 - The Lansing Fraud Matter, Part 1.flac | 283
Yours Truly, Johnny Dollar - 1955-12-13 - 282 - The Lansing Fraud Matter, Part 2.flac | 284
Yours Truly, Johnny Dollar - 1955-12-14 - 283 - The Lansing Fraud Matter, Part 3.flac | 285
Yours Truly, Johnny Dollar - 1955-12-15 - 284 - The Lansing Fraud Matter, Part 4.flac | 286
Yours Truly, Johnny Dollar - 1955-12-16 - 285 - The Lansing Fraud Matter, Part 5.flac | 287
Yours Truly, Johnny Dollar - 1955-12-19 - 286 - The Nick Shurn Matter, Part 1.flac | 288
Yours Truly, Johnny Dollar - 1955-12-20 - 287 - The Nick Shurn Matter, Part 2.flac | 289
Yours Truly, Johnny Dollar - 1955-12-21 - 288 - The Nick Shurn Matter, Part 3.flac | 290
Yours Truly, Johnny Dollar - 1955-12-22 - 289 - The Nick Shurn Matter, Part 4.flac | 291
Yours Truly, Johnny Dollar - 1955-12-23 - 290 - The Nick Shurn Matter, Part 5.flac | 292
Yours Truly, Johnny Dollar - 1955-12-26 - 291 - The Forbes Matter, Part 1.flac | 293
Yours Truly, Johnny Dollar - 1955-12-27 - 292 - The Forbes Matter, Part 2.flac | 294
Yours Truly, Johnny Dollar - 1955-12-28 - 293 - The Forbes Matter, Part 3.flac | 295
Yours Truly, Johnny Dollar - 1955-12-29 - 294 - The Forbes Matter, Part 4.flac | 296
Yours Truly, Johnny Dollar - 1955-12-30 - 295 - The Forbes Matter, Part 5.flac | 297
Yours Truly, Johnny Dollar - 1956-01-02 - 296 - The Caylin Matter, Part 1.flac | 298
Yours Truly, Johnny Dollar - 1956-01-03 - 297 - The Caylin Matter, Part 2.flac | 299
Yours Truly, Johnny Dollar - 1956-01-04 - 298 - The Caylin Matter, Part 3.flac | 300
Yours Truly, Johnny Dollar - 1956-01-05 - 299 - The Caylin Matter, Part 4.flac | 301
Yours Truly, Johnny Dollar - 1956-01-06 - 300 - The Caylin Matter, Part 5.flac | 302
Yours Truly, Johnny Dollar - 1956-01-09 - 301 - The Todd Matter, Part 1.flac | 303
Yours Truly, Johnny Dollar - 1956-01-10 - 302 - The Todd Matter, Part 2.flac | 304
Yours Truly, Johnny Dollar - 1956-01-11 - 303 - The Todd Matter, Part 3.flac | 305
Yours Truly, Johnny Dollar - 1956-01-12 - 304 - The Todd Matter, Part 4.flac | 306
Yours Truly, Johnny Dollar - 1956-01-13 - 305 - The Todd Matter, Part 5.flac | 307
Yours Truly, Johnny Dollar - 1956-01-16 - 306 - The Ricardo Amerigo Matter, Part 1.flac | 308
Yours Truly, Johnny Dollar - 1956-01-17 - 307 - The Ricardo Amerigo Matter, Part 2.flac | 309
Yours Truly, Johnny Dollar - 1956-01-18 - 308 - The Ricardo Amerigo Matter, Part 3.flac | 310
Yours Truly, Johnny Dollar - 1956-01-19 - 309 - The Ricardo Amerigo Matter, Part 4.flac | 311
Yours Truly, Johnny Dollar - 1956-01-20 - 310 - The Ricardo Amerigo Matter, Part 5.flac | 312
Yours Truly, Johnny Dollar - 1956-01-23 - 311 - The Duke Red Matter, Part 1.flac | 313
Yours Truly, Johnny Dollar - 1956-01-24 - 312 - The Duke Red Matter, Part 2.flac | 314
Yours Truly, Johnny Dollar - 1956-01-25 - 313 - The Duke Red Matter, Part 3.flac | 315
Yours Truly, Johnny Dollar - 1956-01-26 - 314 - The Duke Red Matter, Part 4.flac | 316
Yours Truly, Johnny Dollar - 1956-01-27 - 315 - The Duke Red Matter, Part 5.flac | 317
Yours Truly, Johnny Dollar - 1956-01-30 - 316 - The Flight Six Matter, Part 1.flac | 318
Yours Truly, Johnny Dollar - 1956-01-31 - 317 - The Flight Six Matter, Part 2.flac | 319
Yours Truly, Johnny Dollar - 1956-02-01 - 318 - The Flight Six Matter, Part 3.flac | 320
Yours Truly, Johnny Dollar - 1956-02-02 - 319 - The Flight Six Matter, Part 4.flac | 321
Yours Truly, Johnny Dollar - 1956-02-03 - 320 - The Flight Six Matter, Part 5.flac | 322
Yours Truly, Johnny Dollar - 1956-02-06 - 321 - The McClain Matter, Part 1.flac | 323
Yours Truly, Johnny Dollar - 1956-02-07 - 322 - The McClain Matter, Part 2.flac | 324
Yours Truly, Johnny Dollar - 1956-02-09 - 324 - The McClain Matter, Part 4.flac | 326
Yours Truly, Johnny Dollar - 1956-02-10 - 325 - The McClain Matter, Part 5.flac | 327
Yours Truly, Johnny Dollar - 1956-02-13 - 326 - The Cui Bono Matter, Part 1.flac | 328
Yours Truly, Johnny Dollar - 1956-02-14 - 327 - The Cui Bono Matter, Part 2.flac | 329
Yours Truly, Johnny Dollar - 1956-02-15 - 328 - The Cui Bono Matter, Part 3.flac | 330
Yours Truly, Johnny Dollar - 1956-02-16 - 329 - The Cui Bono Matter, Part 4.flac | 331
Yours Truly, Johnny Dollar - 1956-02-17 - 330 - The Cui Bono Matter, Part 5.flac | 332
Yours Truly, Johnny Dollar - 1956-02-20 - 331 - The Bennet Matter, Part 1.flac | 333
Yours Truly, Johnny Dollar - 1956-02-21 - 332 - The Bennet Matter, Part 2.flac | 334
Yours Truly, Johnny Dollar - 1956-02-22 - 333 - The Bennet Matter, Part 3.flac | 335
Yours Truly, Johnny Dollar - 1956-02-23 - 334 - The Bennet Matter, Part 4.flac | 336
Yours Truly, Johnny Dollar - 1956-02-24 - 335 - The Bennet Matter, Part 5.flac | 337
Yours Truly, Johnny Dollar - 1956-02-27 - 336 - The Fathom-Five Matter, Part 1.flac | 338
Yours Truly, Johnny Dollar - 1956-02-28 - 337 - The Fathom-Five Matter, Part 2.flac | 339
Yours Truly, Johnny Dollar - 1956-02-29 - 338 - The Fathom-Five Matter, Part 3.flac | 340
Yours Truly, Johnny Dollar - 1956-03-01 - 339 - The Fathom-Five Matter, Part 4.flac | 341
Yours Truly, Johnny Dollar - 1956-03-02 - 340 - The Fathom-Five Matter, Part 5.flac | 342
Yours Truly, Johnny Dollar - 1956-03-05 - 341 - The Plantagent Matter, Part 1.flac | 343
Yours Truly, Johnny Dollar - 1956-03-06 - 342 - The Plantagent Matter, Part 2.flac | 344
Yours Truly, Johnny Dollar - 1956-03-07 - 343 - The Plantagent Matter, Part 3.flac | 345
Yours Truly, Johnny Dollar - 1956-03-08 - 344 - The Plantagent Matter, Part 4.flac | 346
Yours Truly, Johnny Dollar - 1956-03-09 - 345 - The Plantagent Matter, Part 5.flac | 347
Yours Truly, Johnny Dollar - 1956-03-12 - 346 - The Clinton Matter, Part 1.flac | 348
Yours Truly, Johnny Dollar - 1956-03-13 - 347 - The Clinton Matter, Part 2.flac | 349
Yours Truly, Johnny Dollar - 1956-03-14 - 348 - The Clinton Matter, Part 3.flac | 350
Yours Truly, Johnny Dollar - 1956-03-15 - 349 - The Clinton Matter, Part 4.flac | 351
Yours Truly, Johnny Dollar - 1956-03-16 - 350 - The Clinton Matter, Part 5.flac | 352
Yours Truly, Johnny Dollar - 1956-03-19 - 351 - The Jolly Roger Fraud Matter, Part 1.flac | 353
Yours Truly, Johnny Dollar - 1956-03-20 - 352 - The Jolly Roger Fraud Matter, Part 2.flac | 354
Yours Truly, Johnny Dollar - 1956-03-21 - 353 - The Jolly Roger Fraud Matter, Part 3.flac | 355
Yours Truly, Johnny Dollar - 1956-03-22 - 354 - The Jolly Roger Fraud Matter, Part 4.flac | 356
Yours Truly, Johnny Dollar - 1956-03-23 - 355 - The Jolly Roger Fraud Matter, Part 5.flac | 357
Yours Truly, Johnny Dollar - 1956-03-26 - 356 - The LaMarr Matter, Part 1.flac | 358
Yours Truly, Johnny Dollar - 1956-03-27 - 357 - The LaMarr Matter, Part 2.flac | 359
Yours Truly, Johnny Dollar - 1956-03-28 - 358 - The LaMarr Matter, Part 3.flac | 360
Yours Truly, Johnny Dollar - 1956-03-29 - 359 - The LaMarr Matter, Part 4.flac | 361
Yours Truly, Johnny Dollar - 1956-03-30 - 360 - The LaMarr Matter, Part 5.flac | 362
Yours Truly, Johnny Dollar - 1956-04-02 - 361 - The Salt City Matter, Part 1.flac | 363
Yours Truly, Johnny Dollar - 1956-04-04 - 363 - The Salt City Matter, Part 3.flac | 365
Yours Truly, Johnny Dollar - 1956-04-05 - 364 - The Salt City Matter, Part 4.flac | 366
Yours Truly, Johnny Dollar - 1956-04-06 - 365 - The Salt City Matter, Part 5.flac | 367
Yours Truly, Johnny Dollar - 1956-04-09 - 366 - The Laird Douglas Douglas Of Heatherscote Matter, Part 1.flac | 368
Yours Truly, Johnny Dollar - 1956-04-10 - 367 - The Laird Douglas Douglas Of Heatherscote Matter, Part 2.flac | 369
Yours Truly, Johnny Dollar - 1956-04-11 - 368 - The Laird Douglas Douglas Of Heatherscote Matter, Part 3.flac | 370
Yours Truly, Johnny Dollar - 1956-04-12 - 369 - The Laird Douglas Douglas Of Heatherscote Matter, Part 4.flac | 371
Yours Truly, Johnny Dollar - 1956-04-13 - 370 - The Laird Douglas Douglas Of Heatherscote Matter, Part 5.flac | 372
Yours Truly, Johnny Dollar - 1956-04-16 - 371 - The Shepherd Matter, Part 1.flac | 373
Yours Truly, Johnny Dollar - 1956-04-17 - 372 - The Shepherd Matter, Part 2.flac | 374
Yours Truly, Johnny Dollar - 1956-04-18 - 373 - The Shepherd Matter, Part 3.flac | 375
Yours Truly, Johnny Dollar - 1956-04-19 - 374 - The Shepherd Matter, Part 4.flac | 376
Yours Truly, Johnny Dollar - 1956-04-20 - 375 - The Shepherd Matter, Part 5.flac | 377
Yours Truly, Johnny Dollar - 1956-04-23 - 376 - The Lonely Hearts Matter, Part 1.flac | 378
Yours Truly, Johnny Dollar - 1956-04-24 - 377 - The Lonely Hearts Matter, Part 2.flac | 379
Yours Truly, Johnny Dollar - 1956-04-25 - 378 - The Lonely Hearts Matter, Part 3.flac | 380
Yours Truly, Johnny Dollar - 1956-04-27 - 380 - The Lonely Hearts Matter, Part 5.flac | 382
Yours Truly, Johnny Dollar - 1956-04-30 - 381 - The Callicles Matter, Part 1.flac | 383
Yours Truly, Johnny Dollar - 1956-05-01 - 382 - The Callicles Matter, Part 2.flac | 384
Yours Truly, Johnny Dollar - 1956-05-02 - 383 - The Callicles Matter, Part 3.flac | 385
Yours Truly, Johnny Dollar - 1956-05-03 - 384 - The Callicles Matter, Part 4.flac | 386
Yours Truly, Johnny Dollar - 1956-05-04 - 385 - The Callicles Matter, Part 5.flac | 387
Yours Truly, Johnny Dollar - 1956-05-07 - 386 - The Silver Blue Matter, Part 1.flac | 388
Yours Truly, Johnny Dollar - 1956-05-08 - 387 - The Silver Blue Matter, Part 2.flac | 389
Yours Truly, Johnny Dollar - 1956-05-09 - 388 - The Silver Blue Matter, Part 3.flac | 390
Yours Truly, Johnny Dollar - 1956-05-10 - 389 - The Silver Blue Matter, Part 4.flac | 391
Yours Truly, Johnny Dollar - 1956-05-11 - 390 - The Silver Blue Matter, Part 5.flac | 392
Yours Truly, Johnny Dollar - 1956-05-14 - 391 - The Matter Of The Medium, Well Done, Part 1.flac | 393
Yours Truly, Johnny Dollar - 1956-05-15 - 392 - The Matter Of The Medium, Well Done, Part 2.flac | 394
Yours Truly, Johnny Dollar - 1956-05-16 - 393 - The Matter Of The Medium, Well Done, Part 3.flac | 395
Yours Truly, Johnny Dollar - 1956-05-17 - 394 - The Matter Of The Medium, Well Done, Part 4.flac | 396
Yours Truly, Johnny Dollar - 1956-05-18 - 395 - The Matter Of The Medium, Well Done, Part 5.flac | 397
Yours Truly, Johnny Dollar - 1956-05-21 - 396 - The Tears Of Night Matter, Part 1.flac | 398
Yours Truly, Johnny Dollar - 1956-05-22 - 397 - The Tears Of Night Matter, Part 2.flac | 399
Yours Truly, Johnny Dollar - 1956-05-23 - 398 - The Tears Of Night Matter, Part 3.flac | 400
Yours Truly, Johnny Dollar - 1956-05-24 - 399 - The Tears Of Night Matter, Part 4.flac | 401
Yours Truly, Johnny Dollar - 1956-05-25 - 400 - The Tears Of Night Matter, Part 5.flac | 402
Yours Truly, Johnny Dollar - 1956-05-28 - 401 - The Matter Of Reasonable Doubt, Part 1.flac | 403
Yours Truly, Johnny Dollar - 1956-05-29 - 402 - The Matter Of Reasonable Doubt, Part 2.flac | 404
Yours Truly, Johnny Dollar - 1956-05-30 - 403 - The Matter Of Reasonable Doubt, Part 3.flac | 405
Yours Truly, Johnny Dollar - 1956-05-31 - 404 - The Matter Of Reasonable Doubt, Part 4.flac | 406
Yours Truly, Johnny Dollar - 1956-06-01 - 405 - The Matter Of Reasonable Doubt, Part 5.flac | 407
Yours Truly, Johnny Dollar - 1956-06-04 - 406 - The Indestructible Mike Matter, Part 1.flac | 408
Yours Truly, Johnny Dollar - 1956-06-05 - 407 - The Indestructible Mike Matter, Part 2.flac | 409
Yours Truly, Johnny Dollar - 1956-06-06 - 408 - The Indestructible Mike Matter, Part 3.flac | 410
Yours Truly, Johnny Dollar - 1956-06-07 - 409 - The Indestructible Mike Matter, Part 4.flac | 411
Yours Truly, Johnny Dollar - 1956-06-08 - 410 - The Indestructible Mike Matter, Part 5.flac | 412
Yours Truly, Johnny Dollar - 1956-06-11 - 411 - The Laughing Matter, Part 1.flac | 413
Yours Truly, Johnny Dollar - 1956-06-12 - 412 - The Laughing Matter, Part 2.flac | 414
Yours Truly, Johnny Dollar - 1956-06-13 - 413 - The Laughing Matter, Part 3.flac | 415
Yours Truly, Johnny Dollar - 1956-06-14 - 414 - The Laughing Matter, Part 4.flac | 416
Yours Truly, Johnny Dollar - 1956-06-15 - 415 - The Laughing Matter, Part 5.flac | 417
Yours Truly, Johnny Dollar - 1956-06-18 - 416 - The Pearling Matter, Part 1.flac | 418
Yours Truly, Johnny Dollar - 1956-06-19 - 417 - The Pearling Matter, Part 2.flac | 419
Yours Truly, Johnny Dollar - 1956-06-20 - 418 - The Pearling Matter, Part 3.flac | 420
Yours Truly, Johnny Dollar - 1956-06-21 - 419 - The Pearling Matter, Part 4.flac | 421
Yours Truly, Johnny Dollar - 1956-06-22 - 420 - The Pearling Matter, Part 5.flac | 422
Yours Truly, Johnny Dollar - 1956-06-25 - 421 - The Long Shot Matter, Part 1.flac | 423
Yours Truly, Johnny Dollar - 1956-06-26 - 422 - The Long Shot Matter, Part 2.flac | 424
Yours Truly, Johnny Dollar - 1956-06-27 - 423 - The Long Shot Matter, Part 3.flac | 425
Yours Truly, Johnny Dollar - 1956-06-28 - 424 - The Long Shot Matter, Part 4.flac | 426
Yours Truly, Johnny Dollar - 1956-06-29 - 425 - The Long Shot Matter, Part 5.flac | 427
Yours Truly, Johnny Dollar - 1956-07-02 - 426 - The Midas Touch Matter, Part 1.flac | 428
Yours Truly, Johnny Dollar - 1956-07-03 - 427 - The Midas Touch Matter, Part 2.flac | 429
Yours Truly, Johnny Dollar - 1956-07-04 - 428 - The Midas Touch Matter, Part 3.flac | 430
Yours Truly, Johnny Dollar - 1956-07-05 - 429 - The Midas Touch Matter, Part 4.flac | 431
Yours Truly, Johnny Dollar - 1956-07-06 - 430 - The Midas Touch Matter, Part 5.flac | 432
Yours Truly, Johnny Dollar - 1956-07-09 - 431 - The Shady Lane Matter, Part 1.flac | 433
Yours Truly, Johnny Dollar - 1956-07-10 - 432 - The Shady Lane Matter, Part 2.flac | 434
Yours Truly, Johnny Dollar - 1956-07-11 - 433 - The Shady Lane Matter, Part 3.flac | 435
Yours Truly, Johnny Dollar - 1956-07-12 - 434 - The Shady Lane Matter, Part 4.flac | 436
Yours Truly, Johnny Dollar - 1956-07-13 - 435 - The Shady Lane Matter, Part 5.flac | 437
Yours Truly, Johnny Dollar - 1956-07-16 - 436 - The Star Of Capetown Matter, Part 1.flac | 438
Yours Truly, Johnny Dollar - 1956-07-17 - 437 - The Star Of Capetown Matter, Part 2.flac | 439
Yours Truly, Johnny Dollar - 1956-07-18 - 438 - The Star Of Capetown Matter, Part 3.flac | 440
Yours Truly, Johnny Dollar - 1956-07-19 - 439 - The Star Of Capetown Matter, Part 4.flac | 441
Yours Truly, Johnny Dollar - 1956-07-20 - 440 - The Star Of Capetown Matter, Part 5.flac | 442
Yours Truly, Johnny Dollar - 1956-07-23 - 441 - The Open Town Matter, Part 1.flac | 443
Yours Truly, Johnny Dollar - 1956-07-24 - 442 - The Open Town Matter, Part 2.flac | 444
Yours Truly, Johnny Dollar - 1956-07-25 - 443 - The Open Town Matter, Part 3.flac | 445
Yours Truly, Johnny Dollar - 1956-07-26 - 444 - The Open Town Matter, Part 4.flac | 446
Yours Truly, Johnny Dollar - 1956-07-27 - 445 - The Open Town Matter, Part 5.flac | 447
Yours Truly, Johnny Dollar - 1956-07-30 - 446 - The Sea Legs Matter, Part 1.flac | 448
Yours Truly, Johnny Dollar - 1956-07-31 - 447 - The Sea Legs Matter, Part 2.flac | 449
Yours Truly, Johnny Dollar - 1956-08-01 - 448 - The Sea Legs Matter, Part 3.flac | 450
Yours Truly, Johnny Dollar - 1956-08-02 - 449 - The Sea Legs Matter, Part 4.flac | 451
Yours Truly, Johnny Dollar - 1956-08-03 - 450 - The Sea Legs Matter, Part 5.flac | 452
Yours Truly, Johnny Dollar - 1956-08-06 - 451 - The Alder Matter, Part 1.flac | 453
Yours Truly, Johnny Dollar - 1956-08-07 - 452 - The Alder Matter, Part 2.flac | 454
Yours Truly, Johnny Dollar - 1956-08-08 - 453 - The Alder Matter, Part 3.flac | 455
Yours Truly, Johnny Dollar - 1956-08-09 - 454 - The Alder Matter, Part 4.flac | 456
Yours Truly, Johnny Dollar - 1956-08-10 - 455 - The Alder Matter, Part 5.flac | 457
Yours Truly, Johnny Dollar - 1956-08-13 - 456 - The Crystal Lake Matter, Part 1.flac | 458
Yours Truly, Johnny Dollar - 1956-08-14 - 457 - The Crystal Lake Matter, Part 2.flac | 459
Yours Truly, Johnny Dollar - 1956-08-15 - 458 - The Crystal Lake Matter, Part 3.flac | 460
Yours Truly, Johnny Dollar - 1956-08-16 - 459 - The Crystal Lake Matter, Part 4.flac | 461
Yours Truly, Johnny Dollar - 1956-08-17 - 460 - The Crystal Lake Matter, Part 5.flac | 462
Yours Truly, Johnny Dollar - 1956-08-24 - 461 - The Kranesburg Matter, Part 1.flac | 463
Yours Truly, Johnny Dollar - 1956-08-27 - 462 - The Kranesburg Matter, Part 2.flac | 464
Yours Truly, Johnny Dollar - 1956-08-28 - 463 - The Kranesburg Matter, Part 3.flac | 465
Yours Truly, Johnny Dollar - 1956-08-29 - 464 - The Kranesburg Matter, Part 4.flac | 466
Yours Truly, Johnny Dollar - 1956-08-30 - 465 - The Kranesburg Matter, Part 5.flac | 467
Yours Truly, Johnny Dollar - 1956-08-31 - 466 - The Kranesburg Matter, Part 6.flac | 468
Yours Truly, Johnny Dollar - 1956-09-03 - 467 - The Curse Of Kamashek Matter, Part 1.flac | 469
Yours Truly, Johnny Dollar - 1956-09-04 - 468 - The Curse Of Kamashek Matter, Part 2.flac | 470
Yours Truly, Johnny Dollar - 1956-09-05 - 469 - The Curse Of Kamashek Matter, Part 3.flac | 471
Yours Truly, Johnny Dollar - 1956-09-06 - 470 - The Curse Of Kamashek Matter, Part 4.flac | 472
Yours Truly, Johnny Dollar - 1956-09-07 - 471 - The Curse Of Kamashek Matter, Part 5.flac | 473
Yours Truly, Johnny Dollar - 1956-09-10 - 472 - The Confidential Matter, Part 1.flac | 474
Yours Truly, Johnny Dollar - 1956-09-11 - 473 - The Confidential Matter, Part 2.flac | 475
Yours Truly, Johnny Dollar - 1956-09-12 - 474 - The Confidential Matter, Part 3.flac | 476
Yours Truly, Johnny Dollar - 1956-09-13 - 475 - The Confidential Matter, Part 4.flac | 477
Yours Truly, Johnny Dollar - 1956-09-14 - 476 - The Confidential Matter, Part 5.flac | 478
Yours Truly, Johnny Dollar - 1956-09-17 - 477 - The Imperfect Alibi Matter, Part 1.flac | 479
Yours Truly, Johnny Dollar - 1956-09-19 - 479 - The Imperfect Alibi Matter, Part 3.flac | 481
Yours Truly, Johnny Dollar - 1956-09-20 - 480 - The Imperfect Alibi Matter, Part 4.flac | 482
Yours Truly, Johnny Dollar - 1956-09-21 - 481 - The Imperfect Alibi Matter, Part 5.flac | 483
Yours Truly, Johnny Dollar - 1956-09-24 - 482 - The Meg's Palace Matter, Part 1.flac | 484
Yours Truly, Johnny Dollar - 1956-09-25 - 483 - The Meg's Palace Matter, Part 2.flac | 485
Yours Truly, Johnny Dollar - 1956-09-26 - 484 - The Meg's Palace Matter, Part 3.flac | 486
Yours Truly, Johnny Dollar - 1956-09-27 - 485 - The Meg's Palace Matter, Part 4.flac | 487
Yours Truly, Johnny Dollar - 1956-09-28 - 486 - The Meg's Palace Matter, Part 5.flac | 488
Yours Truly, Johnny Dollar - 1956-10-01 - 487 - The Picture Postcard Matter, Part 1.flac | 489
Yours Truly, Johnny Dollar - 1956-10-02 - 488 - The Picture Postcard Matter, Part 2.flac | 490
Yours Truly, Johnny Dollar - 1956-10-03 - 489 - The Picture Postcard Matter, Part 3.flac | 491
Yours Truly, Johnny Dollar - 1956-10-04 - 490 - The Picture Postcard Matter, Part 4.flac | 492
Yours Truly, Johnny Dollar - 1956-10-05 - 491 - The Picture Postcard Matter, Part 5.flac | 493
Yours Truly, Johnny Dollar - 1956-10-08 - 492 - The Primrose Matter, Part 1.flac | 494
Yours Truly, Johnny Dollar - 1956-10-09 - 493 - The Primrose Matter, Part 2.flac | 495
Yours Truly, Johnny Dollar - 1956-10-10 - 494 - The Primrose Matter, Part 3.flac | 496
Yours Truly, Johnny Dollar - 1956-10-11 - 495 - The Primrose Matter, Part 4.flac | 497
Yours Truly, Johnny Dollar - 1956-10-12 - 496 - The Primrose Matter, Part 5.flac | 498
Yours Truly, Johnny Dollar - 1956-10-15 - 497 - The Phantom Chase Matter, Part 1.flac | 499
Yours Truly, Johnny Dollar - 1956-10-16 - 498 - The Phantom Chase Matter, Part 2.flac | 500
Yours Truly, Johnny Dollar - 1956-10-17 - 499 - The Phantom Chase Matter, Part 3.flac | 501
Yours Truly, Johnny Dollar - 1956-10-18 - 500 - The Phantom Chase Matter, Part 4.flac | 502
Yours Truly, Johnny Dollar - 1956-10-19 - 501 - The Phantom Chase Matter, Part 5.flac | 503
Yours Truly, Johnny Dollar - 1956-10-22 - 502 - The Phantom Chase Matter, Part 6.flac | 504
Yours Truly, Johnny Dollar - 1956-10-24 - 503 - The Phantom Chase Matter, Part 7.flac | 505
Yours Truly, Johnny Dollar - 1956-10-25 - 504 - The Phantom Chase Matter, Part 8.flac | 506
Yours Truly, Johnny Dollar - 1956-10-26 - 505 - The Phantom Chase Matter, Part 9.flac | 507
Yours Truly, Johnny Dollar - 1956-10-29 - 506 - The Silent Queen Matter, Part 1.flac | 508
Yours Truly, Johnny Dollar - 1956-10-30 - 507 - The Silent Queen Matter, Part 2.flac | 509
Yours Truly, Johnny Dollar - 1956-10-31 - 508 - The Silent Queen Matter, Part 3.flac | 510
Yours Truly, Johnny Dollar - 1956-11-01 - 509 - The Silent Queen Matter, Part 4.flac | 511
Yours Truly, Johnny Dollar - 1956-11-02 - 510 - The Silent Queen Matter, Part 5.flac | 512
Yours Truly, Johnny Dollar - 1956-11-11 - 511 - The Big Scoop Matter.flac | 513
Yours Truly, Johnny Dollar - 1956-11-18 - 512 - The Markham Matter.flac | 514
Yours Truly, Johnny Dollar - 1956-11-25 - 513 - The Royal Street Matter.flac | 515
Yours Truly, Johnny Dollar - 1956-12-09 - 514 - The Burning Carr Matter.flac | 516
Yours Truly, Johnny Dollar - 1956-12-16 - 515 - The Rasmussen Matter.flac | 517
Yours Truly, Johnny Dollar - 1956-12-23 - 516 - The Missing Mouse Matter.flac | 518
Yours Truly, Johnny Dollar - 1956-12-30 - 517 - The Squared Circle Matter.flac | 519
Yours Truly, Johnny Dollar - 1957-01-06 - 518 - The Ellen Dear Matter.mp3 | 520
Yours Truly, Johnny Dollar - 1957-01-13 - 519 - The Desalles Matter.mp3 | 521
Yours Truly, Johnny Dollar - 1957-01-20 - 520 - The Blooming Blossom Matter.mp3 | 522
Yours Truly, Johnny Dollar - 1957-01-27 - 521 - The Mad Hatter Matter.flac | 523
Yours Truly, Johnny Dollar - 1957-02-03 - 522 - The Kirbey Will Matter.flac | 524
Yours Truly, Johnny Dollar - 1957-02-10 - 523 - The Templeton Matter.flac | 525
Yours Truly, Johnny Dollar - 1957-03-03 - 525 - The Meek Memorial Matter.flac | 527
Yours Truly, Johnny Dollar - 1957-03-10 - 526 - The Suntan Oil Matter.flac | 528
Yours Truly, Johnny Dollar - 1957-03-17 - 527 - The Clever Chemist Matter.flac | 529
Yours Truly, Johnny Dollar - 1957-04-14 - 530 - The Ming Toy Murphy Matter.mp3 | 532
Yours Truly, Johnny Dollar - 1957-04-28 - 532 - The Melancholy Memory Matter.mp3 | 534
Yours Truly, Johnny Dollar - 1957-05-05 - 533 - The Peerless Fire Matter.flac | 535
Yours Truly, Johnny Dollar - 1957-05-19 - 535 - The Michael Meany Mirage Matter.mp3 | 537
Yours Truly, Johnny Dollar - 1957-05-26 - 536 - The Wayward Truck Matter.flac | 538
Yours Truly, Johnny Dollar - 1957-06-02 - 537 - The Loss Of Memory Matter.mp3 | 539
Yours Truly, Johnny Dollar - 1957-06-09 - 538 - The Mason-Dixon Mismatch Matter.flac | 540
Yours Truly, Johnny Dollar - 1957-06-16 - 539 - The Dixon Murder Matter.flac | 541
Yours Truly, Johnny Dollar - 1957-06-23 - 540 - The Parley Barron Matter.mp3 | 542
Yours Truly, Johnny Dollar - 1957-06-30 - 541 - The Funny Money Matter.flac | 543
Yours Truly, Johnny Dollar - 1957-07-07 - 542 - The Felicity Feline Matter.flac | 544
Yours Truly, Johnny Dollar - 1957-07-14 - 543 - The Heatherstone Players Matter.flac | 545
Yours Truly, Johnny Dollar - 1957-07-21 - 544 - The Yours Truly Matter.flac | 546
Yours Truly, Johnny Dollar - 1957-07-28 - 545 - The Confederate Coinage Matter.flac | 547
Yours Truly, Johnny Dollar - 1957-08-04 - 546 - The Wayward Widow Matter.flac | 548
Yours Truly, Johnny Dollar - 1957-08-11 - 547 - The Killer's Brand Matter.flac | 549
Yours Truly, Johnny Dollar - 1957-08-25 - 549 - The Smoky Sleeper Matter.flac | 551
Yours Truly, Johnny Dollar - 1957-09-01 - 550 - The Poor Little Rich Girl Matter.flac | 552
Yours Truly, Johnny Dollar - 1957-09-08 - 551 - The Charmona Matter.flac | 553
Yours Truly, Johnny Dollar - 1957-09-15 - 552 - The J.P.D. Matter.flac | 554
Yours Truly, Johnny Dollar - 1957-09-22 - 553 - The Ideal Vacation Matter.mp3 | 555
Yours Truly, Johnny Dollar - 1957-09-29 - 554 - The Doubtful Dairy Matter.flac | 556
Yours Truly, Johnny Dollar - 1957-10-06 - 555 - The Bum Steer Matter.flac | 557
Yours Truly, Johnny Dollar - 1957-10-13 - 556 - The Silver Belle Matter.flac | 558
Yours Truly, Johnny Dollar - 1957-10-20 - 557 - The Mary Grace Matter.flac | 559
Yours Truly, Johnny Dollar - 1957-10-27 - 558 - The Three Sisters Matter.mp3 | 560
Yours Truly, Johnny Dollar - 1957-11-03 - 559 - The Model Picture Matter.flac | 561
Yours Truly, Johnny Dollar - 1957-11-10 - 560 - The Alkali Mike Matter.mp3 | 562
Yours Truly, Johnny Dollar - 1957-11-17 - 561 - The Shy Beneficiary Matter.mp3 | 563
Yours Truly, Johnny Dollar - 1957-11-24 - 562 - The Hope To Die Matter.mp3 | 564
Yours Truly, Johnny Dollar - 1957-12-01 - 563 - The Sunny Dream Matter.flac | 565
Yours Truly, Johnny Dollar - 1957-12-08 - 564 - The Hapless Hunter Matter.mp3 | 566
Yours Truly, Johnny Dollar - 1957-12-15 - 565 - The Happy Family Matter.flac | 567
Yours Truly, Johnny Dollar - 1957-12-22 - 566 - The Carmen Kringle Matter.flac | 568
Yours Truly, Johnny Dollar - 1957-12-29 - 567 - The Latin Lovely Matter.mp3 | 569
Yours Truly, Johnny Dollar - 1958-01-05 - 568 - The Ingenuous Jeweler Matter.mp3 | 570
Yours Truly, Johnny Dollar - 1958-01-12 - 569 - The Boron 112 Matter.mp3 | 571
Yours Truly, Johnny Dollar - 1958-01-19 - 570 - The Eleven O'Clock Matter.flac | 572
Yours Truly, Johnny Dollar - 1958-01-26 - 569 - The Fire In Paradise Matter.mp3 | 573
Yours Truly, Johnny Dollar - 1958-02-02 - 572 - The Price Of Fame Matter.flac | 574
Yours Truly, Johnny Dollar - 1958-02-09 - 573 - The Sick Chick Matter.mp3 | 575
Yours Truly, Johnny Dollar - 1958-02-16 - 574 - The Time And Tide Matter.flac | 576
Yours Truly, Johnny Dollar - 1958-02-23 - 575 - The Durango Laramie Matter.flac | 577
Yours Truly, Johnny Dollar - 1958-03-02 - 576 - The Diamond Dilemma Matter.flac | 578
Yours Truly, Johnny Dollar - 1958-03-09 - 577 - The Wayward Moth Matter.flac | 579
Yours Truly, Johnny Dollar - 1958-03-16 - 578 - The Salkoff Sequel Matter.flac | 580
Yours Truly, Johnny Dollar - 1958-03-23 - 579 - The Denver Disbursal Matter.flac | 581
Yours Truly, Johnny Dollar - 1958-03-30 - 580 - The Killer's List Matter.flac | 582
Yours Truly, Johnny Dollar - 1958-04-06 - 581 - The Eastern-Western Matter.flac | 583
Yours Truly, Johnny Dollar - 1958-04-13 - 582 - The Wayward Money Matter.flac | 584
Yours Truly, Johnny Dollar - 1958-04-20 - 583 - The Wayward Trout Matter.flac | 585
Yours Truly, Johnny Dollar - 1958-04-27 - 584 - The Village Of Virtue Matter.flac | 586
Yours Truly, Johnny Dollar - 1958-05-04 - 585 - The Carson Arson Matter.flac | 587
Yours Truly, Johnny Dollar - 1958-05-11 - 586 - The Rolling Stone Matter.flac | 588
Yours Truly, Johnny Dollar - 1958-05-18 - 587 - The Ghost To Ghost Matter.flac | 589
Yours Truly, Johnny Dollar - 1958-05-25 - 588 - The Midnite Sun Matter.flac | 590
Yours Truly, Johnny Dollar - 1958-06-01 - 587 - The Froward Fisherman Matter.mp3 | 591
Yours Truly, Johnny Dollar - 1958-06-08 - 590 - The Wayward River Matter.flac | 592
Yours Truly, Johnny Dollar - 1958-06-15 - 591 - The Delectable Damsel Matter.mp3 | 593
Yours Truly, Johnny Dollar - 1958-06-22 - 592 - The Virtuous Mobster Matter.mp3 | 594
Yours Truly, Johnny Dollar - 1958-06-29 - 593 - The Ugly Pattern Matter.flac | 595
Yours Truly, Johnny Dollar - 1958-07-06 - 594 - The Blinker Matter.flac | 596
Yours Truly, Johnny Dollar - 1958-07-13 - 595 - The Mohave Red Matter.flac | 597
Yours Truly, Johnny Dollar - 1958-07-20 - 596 - The Mohave Red Sequel Matter.flac | 598
Yours Truly, Johnny Dollar - 1958-07-27 - 597 - The Wayward Killer Matter.mp3 | 599
Yours Truly, Johnny Dollar - 1958-08-03 - 598 - The Lucky 4 Matter.mp3 | 600
Yours Truly, Johnny Dollar - 1958-08-10 - 599 - The Two Faced Matter.mp3 | 601
Yours Truly, Johnny Dollar - 1958-08-24 - 600 - The Noxious Needle Matter.mp3 | 602
Yours Truly, Johnny Dollar - 1958-09-07 - 602 - The Malibu Mystery Matter.mp3 | 604
Yours Truly, Johnny Dollar - 1958-09-14 - 603 - The Wayward Diamonds Matter.flac | 605
Yours Truly, Johnny Dollar - 1958-09-21 - 604 - The Johnson Payroll Matter.flac | 606
Yours Truly, Johnny Dollar - 1958-09-28 - 605 - The Gruesome Spectacle Matter.flac | 607
Yours Truly, Johnny Dollar - 1958-11-16 - 612 - The Double Trouble Matter.mp3 | 614
Yours Truly, Johnny Dollar - 1958-11-30 - 614 - The Hair Raising Matter.mp3 | 616
Yours Truly, Johnny Dollar - 1959-01-04 - 618 - The Hollywood Mystery Matter.mp3 | 620
Yours Truly, Johnny Dollar - 1959-01-11 - 619 - The Deadly Doubt Matter.mp3 | 621
Yours Truly, Johnny Dollar - 1959-01-25 - 621 - The Doting Dowager Matter.mp3 | 623
Yours Truly, Johnny Dollar - 1959-02-08 - 623 - The Date With Death Matter.flac | 625
Yours Truly, Johnny Dollar - 1959-02-15 - 624 - The Shankar Diamond Matter.flac | 626
Yours Truly, Johnny Dollar - 1959-02-22 - 625 - The Blue Madonna Matter.flac | 627
Yours Truly, Johnny Dollar - 1959-03-08 - 627 - The Net Of Circumstance Matter.mp3 | 629
Yours Truly, Johnny Dollar - 1959-03-15 - 628 - The Baldero Matter.mp3 | 630
Yours Truly, Johnny Dollar - 1959-03-22 - 629 - The Lake Mead Mystery Matter.mp3 | 631
Yours Truly, Johnny Dollar - 1959-03-29 - 630 - The Jimmy Carter Matter.mp3 | 632
Yours Truly, Johnny Dollar - 1959-04-05 - 631 - The Frisco Fire Matter.mp3 | 633
Yours Truly, Johnny Dollar - 1959-04-12 - 632 - The Fairweather Friend Matter.mp3 | 634
Yours Truly, Johnny Dollar - 1959-04-19 - 633 - The Cautious Celibate Matter.flac | 635
Yours Truly, Johnny Dollar - 1959-04-26 - 634 - The Winsome Widow Matter.flac | 636
Yours Truly, Johnny Dollar - 1959-05-10 - 636 - The Fatal Filet Matter.flac | 638
Yours Truly, Johnny Dollar - 1959-05-17 - 637 - The Twin Trouble Matter.mp3 | 639
Yours Truly, Johnny Dollar - 1959-05-24 - 638 - The Casque Of Death Matter.flac | 640
Yours Truly, Johnny Dollar - 1959-05-31 - 639 - The Big H Matter.mp3 | 641
Yours Truly, Johnny Dollar - 1959-06-07 - 640 - The Wayward Heiress Matter.mp3 | 642
Yours Truly, Johnny Dollar - 1959-06-14 - 641 - The Wayward Sculptor Matter.mp3 | 643
Yours Truly, Johnny Dollar - 1959-06-21 - 642 - The Life At Stake Matter.mp3 | 644
Yours Truly, Johnny Dollar - 1959-06-28 - 643 - The Mei-Ling Buddha Matter.mp3 | 645
Yours Truly, Johnny Dollar - 1959-07-05 - 644 - The Only One Butt Matter.mp3 | 646
Yours Truly, Johnny Dollar - 1959-07-12 - 645 - The Frantic Fisherman Matter.mp3 | 647
Yours Truly, Johnny Dollar - 1959-07-19 - 646 - The Will And A Way Matter.mp3 | 648
Yours Truly, Johnny Dollar - 1959-07-26 - 647 - The Bolt Out Of The Blue Matter.mp3 | 649
Yours Truly, Johnny Dollar - 1959-08-02 - 648 - The Deadly Chain Matter.mp3 | 650
Yours Truly, Johnny Dollar - 1959-08-09 - 649 - The Lost By A Hair Matter.mp3 | 651
Yours Truly, Johnny Dollar - 1959-08-16 - 650 - The Night In Paris Matter.mp3 | 652
Yours Truly, Johnny Dollar - 1959-08-23 - 651 - The Embarcadero Matter.mp3 | 653
Yours Truly, Johnny Dollar - 1959-08-30 - 652 - The Really Gone Matter.mp3 | 654
Yours Truly, Johnny Dollar - 1959-09-06 - 653 - The Backfire That Backfired Matter.mp3 | 655
Yours Truly, Johnny Dollar - 1959-09-13 - 654 - The Leumas Matter.mp3 | 656
Yours Truly, Johnny Dollar - 1959-09-20 - 655 - The Little Man Who Was There Matter.mp3 | 657
Yours Truly, Johnny Dollar - 1959-10-04 - 657 - The Buffalo Matter.flac | 658
Yours Truly, Johnny Dollar - 1959-10-11 - 658 - The Further Buffalo Matter.flac | 659
Yours Truly, Johnny Dollar - 1959-10-18 - 659 - The Double Identity Matter.mp3 | 660
Yours Truly, Johnny Dollar - 1959-10-25 - 660 - The Missing Missile Matter.mp3 | 661
Yours Truly, Johnny Dollar - 1959-11-01 - 661 - The Hand Of Providential Matter.mp3 | 662
Yours Truly, Johnny Dollar - 1959-11-08 - 662 - The Larson Arson Matter.flac | 663
Yours Truly, Johnny Dollar - 1959-11-15 - 663 - The Bayou Body Matter.mp3 | 664
Yours Truly, Johnny Dollar - 1959-11-22 - 664 - The Fancy Bridgework Matter.mp3 | 665
Yours Truly, Johnny Dollar - 1959-11-29 - 665 - The Wrong Man Matter.mp3 | 666
Yours Truly, Johnny Dollar - 1959-12-06 - 666 - The Hired Homicide Matter.mp3 | 667
Yours Truly, Johnny Dollar - 1959-12-13 - 667 - The Sudden Wealth Matter.mp3 | 668
Yours Truly, Johnny Dollar - 1959-12-20 - 668 - The Red Mystery Matter.flac | 669
Yours Truly, Johnny Dollar - 1959-12-27 - 669 - The Burning Desire Matter.mp3 | 670
Yours Truly, Johnny Dollar - 1960-01-03 - 670 - The Hapless Ham Matter.mp3 | 671
Yours Truly, Johnny Dollar - 1960-01-10 - 671 - The Unholy Two Matter.mp3 | 672
Yours Truly, Johnny Dollar - 1960-01-17 - 672 - The Evaporated Clue Matter.mp3 | 673
Yours Truly, Johnny Dollar - 1960-01-24 - 673 - The Nuclear Goof Matter.mp3 | 674
Yours Truly, Johnny Dollar - 1960-01-31 - 674 - The Merry-Go-Round Matter.flac | 675
Yours Truly, Johnny Dollar - 1960-02-07 - 675 - The Sidewinder Matter.mp3 | 676
Yours Truly, Johnny Dollar - 1960-02-14 - 676 - The P.O. Matter.mp3 | 677
Yours Truly, Johnny Dollar - 1960-02-21 - 677 - The Alvin's Alfred Matter.mp3 | 678
Yours Truly, Johnny Dollar - 1960-02-28 - 678 - The Look Before The Leap Matter.mp3 | 679
Yours Truly, Johnny Dollar - 1960-03-06 - 679 - The Moonshine Matter.mp3 | 680
Yours Truly, Johnny Dollar - 1960-03-13 - 680 - The Deep Down Matter.mp3 | 681
Yours Truly, Johnny Dollar - 1960-03-20 - 681 - The Saturday Night Matter.mp3 | 682
Yours Truly, Johnny Dollar - 1960-03-27 - 682 - The False Alarm Matter.mp3 | 683
Yours Truly, Johnny Dollar - 1960-04-03 - 683 - The Double Exposure Matter.mp3 | 684
Yours Truly, Johnny Dollar - 1960-04-17 - 684 - The Deadly Swamp Matter.flac | 685
Yours Truly, Johnny Dollar - 1960-04-24 - 685 - The Silver Queen Matter.mp3 | 686
Yours Truly, Johnny Dollar - 1960-05-01 - 686 - The Fatal Switch Matter.mp3 | 687
Yours Truly, Johnny Dollar - 1960-05-08 - 687 - The Phony Phone Matter.mp3 | 688
Yours Truly, Johnny Dollar - 1960-05-15 - 688 - The Mystery Gal Matter.mp3 | 689
Yours Truly, Johnny Dollar - 1960-05-22 - 689 - The Man Who Waits Matter.mp3 | 690
Yours Truly, Johnny Dollar - 1960-05-29 - 690 - The Red Rock Matter.mp3 | 691
Yours Truly, Johnny Dollar - 1960-06-05 - 691 - The Canned Canary Matter.mp3 | 692
Yours Truly, Johnny Dollar - 1960-06-12 - 692 - The Harried Heiress Matter.mp3 | 693
Yours Truly, Johnny Dollar - 1960-06-19 - 693 - The Flask Of Death Matter.mp3 | 694
Yours Truly, Johnny Dollar - 1960-06-26 - 694 - The Wholly Unexpected Matter.flac | 695
Yours Truly, Johnny Dollar - 1960-07-03 - 695 - The Collector's Matter.flac | 696
Yours Truly, Johnny Dollar - 1960-07-17 - 696 - The Back To The Back Matter.flac | 697
Yours Truly, Johnny Dollar - 1960-07-31 - 697 - The Rhymer Collection Matter.mp3 | 698
Yours Truly, Johnny Dollar - 1960-08-14 - 699 - The Paradise Lost Matter.mp3 | 700
Yours Truly, Johnny Dollar - 1960-08-21 - 700 - The Twisted Twin Matter.mp3 | 701
Yours Truly, Johnny Dollar - 1960-08-28 - 701 - The Deadly Debt Matter.flac | 702
Yours Truly, Johnny Dollar - 1960-09-04 - 702 - The Killer Kin Matter.mp3 | 703
Yours Truly, Johnny Dollar - 1960-09-11 - 703 - The Too Much Money Matter.flac | 704
Yours Truly, Johnny Dollar - 1960-09-18 - 704 - The Real Smokey Matter.flac | 705
Yours Truly, Johnny Dollar - 1960-09-25 - 705 - The Five Down Matter.flac | 706
Yours Truly, Johnny Dollar - 1960-10-02 - 706 - The Stope Of Death Matter.flac | 707
Yours Truly, Johnny Dollar - 1960-10-09 - 707 - The Recompense Matter.mp3 | 708
Yours Truly, Johnny Dollar - 1960-10-16 - 708 - The Twins Of Tahoe Matter.mp3 | 709
Yours Truly, Johnny Dollar - 1960-10-23 - 709 - The Unworthy Kin Matter.mp3 | 710
Yours Truly, Johnny Dollar - 1960-10-30 - 710 - The What Goes Matter.mp3 | 711
Yours Truly, Johnny Dollar - 1960-11-06 - 711 - The Super Salesman Matter.mp3 | 712
Yours Truly, Johnny Dollar - 1960-11-13 - 712 - The Bad One Matter.flac | 713
Yours Truly, Johnny Dollar - 1960-11-20 - 713 - The Double Deal Matter.flac | 714
Yours Truly, Johnny Dollar - 1960-11-27 - 714 - The Empty Threat Matter.flac | 715
Yours Truly, Johnny Dollar - 1960-12-04 - 715 - The Earned Income Matter.mp3 | 716
Yours Truly, Johnny Dollar - 1960-12-18 - 717 - The Wayward Kilocycles Matter.mp3 | 718
Yours Truly, Johnny Dollar - 1961-01-08 - 720 - The Paperback Mystery Matter.flac | 724
Yours Truly, Johnny Dollar - 1961-01-15 - 721 - The Very Fishy Matter.mp3 | 722
Yours Truly, Johnny Dollar - 1961-01-29 - 723 - The Short Term Matter.mp3 | 723
Yours Truly, Johnny Dollar - 1961-02-05 - 724 - The Who's Who Matter.flac | 726
Yours Truly, Johnny Dollar - 1961-02-12 - 725 - The Wayward Fireman Matter.flac | 727
Yours Truly, Johnny Dollar - 1961-02-26 - 727 - The Touch-Up Matter.mp3 | 729
Yours Truly, Johnny Dollar - 1961-03-05 - 728 - The Morning After Matter.flac | 730
Yours Truly, Johnny Dollar - 1961-03-12 - 729 - The Ring Of Death Matter.mp3 | 731
Yours Truly, Johnny Dollar - 1961-03-19 - 730 - The Informer Matter.mp3 | 732
Yours Truly, Johnny Dollar - 1961-03-26 - 731 - The Two's A Crowd Matter.mp3 | 733
Yours Truly, Johnny Dollar - 1961-04-02 - 732 - The Wrong Sign Matter.mp3 | 734
Yours Truly, Johnny Dollar - 1961-04-09 - 733 - The Captain's Table Matter.flac | 735
Yours Truly, Johnny Dollar - 1961-04-16 - 734 - The Latrodectus Matter.flac | 736
Yours Truly, Johnny Dollar - 1961-04-23 - 735 - The Rat Pack Matter.mp3 | 737
Yours Truly, Johnny Dollar - 1961-05-14 - 738 - The Simple Simon Matter.mp3 | 740
Yours Truly, Johnny Dollar - 1961-05-21 - 739 - The Lone Wolf Matter.mp3 | 741
Yours Truly, Johnny Dollar - 1961-05-28 - 740 - The Yaak Mystery Matter.flac | 742
Yours Truly, Johnny Dollar - 1961-06-04 - 741 - The Stock-In-Trade Matter.mp3 | 743
Yours Truly, Johnny Dollar - 1961-06-11 - 742 - The Big Date Matter.mp3 | 721
Yours Truly, Johnny Dollar - 1961-06-18 - 743 - The Low Tide Matter.mp3 | 745
Yours Truly, Johnny Dollar - 1961-06-25 - 744 - The Imperfect Crime Matter.mp3 | 746
Yours Truly, Johnny Dollar - 1961-07-02 - 745 - The Well Of Trouble Matter.flac | 747
Yours Truly, Johnny Dollar - 1961-07-09 - 746 - The Fiddle Faddle Matter.mp3 | 748
Yours Truly, Johnny Dollar - 1961-07-16 - 747 - The Old Fashioned Murder Matter.mp3 | 749
Yours Truly, Johnny Dollar - 1961-07-23 - 748 - The Chuckanut Matter.mp3 | 750
Yours Truly, Johnny Dollar - 1961-07-30 - 749 - The Philadelphia Miss Matter.mp3 | 751
Yours Truly, Johnny Dollar - 1961-08-06 - 750 - The Perilous Padre Matter.mp3 | 752
Yours Truly, Johnny Dollar - 1961-08-13 - 751 - The Wrong Doctor Matter.mp3 | 753
Yours Truly, Johnny Dollar - 1961-08-20 - 752 - Too Many Crooks Matter.mp3 | 754
Yours Truly, Johnny Dollar - 1961-08-27 - 753 - The Shifty Looker Matter.mp3 | 755
Yours Truly, Johnny Dollar - 1961-09-03 - 754 - The All-Wet Matter.mp3 | 756
Yours Truly, Johnny Dollar - 1961-09-10 - 755 - The Buyer And The Cellar Matter.mp3 | 757
Yours Truly, Johnny Dollar - 1961-09-24 - 757 - The Double-Barreled Matter.mp3 | 759
Yours Truly, Johnny Dollar - 1961-10-08 - 759 - The Medium Rare Matter.flac | 760
Yours Truly, Johnny Dollar - 1961-10-22 - 761 - The Three For One Matter.mp3 | 762
Yours Truly, Johnny Dollar - 1961-10-29 - 762 - The Bee Or Not To Bee Matter.mp3 | 763
Yours Truly, Johnny Dollar - 1961-11-05 - 763 - The Monticello Mystery Matter.mp3 | 764
Yours Truly, Johnny Dollar - 1961-11-12 - 764 - The Wrong One Matter.mp3 | 765
Yours Truly, Johnny Dollar - 1961-11-19 - 765 - The Guide To Murder Matter.flac | 766
Yours Truly, Johnny Dollar - 1961-11-26 - 766 - The Mad Bomber Matter.mp3 | 767
Yours Truly, Johnny Dollar - 1961-12-03 - 767 - The Cinder Elmer Matter.mp3 | 768
Yours Truly, Johnny Dollar - 1961-12-17 - 769 - The Phony Phone Matter.mp3 | 770
Yours Truly, Johnny Dollar - 1961-12-31 - 770 - The One Too Many Matter.mp3 | 771
Yours Truly, Johnny Dollar - 1962-01-07 - 771 - The Hot Chocolate Matter.mp3 | 772
Yours Truly, Johnny Dollar - 1962-01-21 - 773 - The Terrible Torch Matter.mp3 | 774
Yours Truly, Johnny Dollar - 1962-01-28 - 774 - The Can't Be So Matter.mp3 | 775
Yours Truly, Johnny Dollar - 1962-02-04 - 775 - The Nugget Of Truth Matter.flac | 776
Yours Truly, Johnny Dollar - 1962-02-11 - 776 - The Do It Yourself Matter.mp3 | 777
Yours Truly, Johnny Dollar - 1962-02-18 - 777 - The Takes A Crook Matter.mp3 | 778
Yours Truly, Johnny Dollar - 1962-02-25 - 778 - The Mixed Blessing Matter.mp3 | 779
Yours Truly, Johnny Dollar - 1962-03-04 - 779 - The Top Secret Matter.mp3 | 780
Yours Truly, Johnny Dollar - 1962-03-11 - 780 - The Golden Dream Matter.mp3 | 781
Yours Truly, Johnny Dollar - 1962-03-18 - 781 - The Ike And Mike Matter.flac | 782
Yours Truly, Johnny Dollar - 1962-03-25 - 782 - The Shadow Of A Doubt Matter.flac | 783
Yours Truly, Johnny Dollar - 1962-04-01 - 783 - The Blue Rock Matter.mp3 | 784
Yours Truly, Johnny Dollar - 1962-04-08 - 784 - The Ivy Emerald Matter.mp3 | 785
Yours Truly, Johnny Dollar - 1962-04-15 - 785 - The Wrong Idea Matter.mp3 | 786
Yours Truly, Johnny Dollar - 1962-04-22 - 786 - The Skidmore Matter.mp3 | 787
Yours Truly, Johnny Dollar - 1962-04-29 - 787 - The Grand Canyon Matter.mp3 | 788
Yours Truly, Johnny Dollar - 1962-05-06 - 788 - The Burma Red Matter.mp3 | 789
Yours Truly, Johnny Dollar - 1962-05-13 - 789 - The Lust For Gold Matter.mp3 | 790
Yours Truly, Johnny Dollar - 1962-05-20 - 790 - The Two Steps To Murder Matter.mp3 | 791
Yours Truly, Johnny Dollar - 1962-05-27 - 791 - The Zipp Matter.mp3 | 792
Yours Truly, Johnny Dollar - 1962-06-03 - 792 - The Wayward Gun Matter.mp3 | 793
Yours Truly, Johnny Dollar - 1962-06-17 - 794 - The All Too Easy Matter.mp3 | 795
Yours Truly, Johnny Dollar - 1962-06-24 - 795 - The Hood Of Death Matter.mp3 | 796
Yours Truly, Johnny Dollar - 1962-07-01 - 796 - The Vociferous Dolphin Matter.mp3 | 797
Yours Truly, Johnny Dollar - 1962-07-08 - 797 - The Rilldoe Matter.mp3 | 798
Yours Truly, Johnny Dollar - 1962-07-15 - 798 - The Weather Or Not Matter.mp3 | 799
Yours Truly, Johnny Dollar - 1962-07-22 - 799 - The Skimpy Matter.mp3 | 800
Yours Truly, Johnny Dollar - 1962-07-29 - 800 - The Four Is A Crowd Matter.mp3 | 801
Yours Truly, Johnny Dollar - 1962-08-05 - 801 - The Case Of Trouble Matter.mp3 | 802
Yours Truly, Johnny Dollar - 1962-08-12 - 802 - The Oldest Gag Matter.mp3 | 803
Yours Truly, Johnny Dollar - 1962-08-19 - 803 - The Lorelei Matter.mp3 | 804
Yours Truly, Johnny Dollar - 1962-08-26 - 804 - The Gold Rush Matter.mp3 | 805
Yours Truly, Johnny Dollar - 1962-09-02 - 805 - The Doninger Doninger Matter.mp3 | 806
Yours Truly, Johnny Dollar - 1962-09-09 - 806 - The Four Cs Matter.mp3 | 807
Yours Truly, Johnny Dollar - 1962-09-16 - 807 - The No Matter Matter.mp3 | 808
Yours Truly, Johnny Dollar - 1962-09-23 - 808 - The Deadly Crystal Matter.mp3 | 809
Yours Truly, Johnny Dollar - 1962-09-30 - 809 - The Tip-Off Matter.flac | 810
""".strip().split("\n")

script_first_pages_lines = """
Yours Truly, Johnny Dollar - 1948-12-06 - 000 - Yours Truly, Lloyd London (Dick Powell Audition).jpg | 0
Yours Truly, Johnny Dollar - 1949-07-17 - 010 - Here Comes The Death Of The Party.jpg | 11
Yours Truly, Johnny Dollar - 1949-08-07 - 013 - Murder Ain't Minor.jpg | 14
Yours Truly, Johnny Dollar - 1949-08-14 - 014 - Death Takes A Working Day.jpg | 15
Yours Truly, Johnny Dollar - 1949-08-21 - 015 - Out Of The Fire, Into The Frying Pan.jpg | 16
Yours Truly, Johnny Dollar - 1949-08-28 - 016 - How I Turned A Luxury Liner Into A Battleship.jpg | 17
Yours Truly, Johnny Dollar - 1950-02-03 - 034 - Death Takes A Working Day.jpg | 35
Yours Truly, Johnny Dollar - 1950-02-17 - 040 - The Gravedigger's Spades.jpg | 37
Yours Truly, Johnny Dollar - 1950-02-24 - 037 - The Archeologist.jpg | 38
Yours Truly, Johnny Dollar - 1950-03-21 - 041 - The Man Who Wrote Himself To Death.jpg | 42
Yours Truly, Johnny Dollar - 1950-03-28 - 042 - The Village Scene.jpg | 43
Yours Truly, Johnny Dollar - 1950-04-25 - 046 - Pearl Carrasa.jpg | 47
Yours Truly, Johnny Dollar - 1950-11-18 - 072 - The Nora Falkner Matter.jpg | 73
Yours Truly, Johnny Dollar - 1950-11-25 - 073 - The Woodward, Manila, Matter.jpg | 74
Yours Truly, Johnny Dollar - 1950-12-02 - 074 - The Blackburn Matter.jpg | 75
Yours Truly, Johnny Dollar - 1950-12-23 - 075 - The Montevideo Matter.jpg | 76
Yours Truly, Johnny Dollar - 1950-12-30 - 076 - The Rudy Valentine Matter.jpg | 77
Yours Truly, Johnny Dollar - 1951-01-06 - 077 - The Adolph Shoman Matter.jpg | 78
Yours Truly, Johnny Dollar - 1951-01-13 - 078 - The Port-O-Call Matter.jpg | 79
Yours Truly, Johnny Dollar - 1951-01-20 - 079 - The David Rockey Matter.jpg | 80
Yours Truly, Johnny Dollar - 1951-01-27 - 080 - The Weldon Bragg Matter.jpg | 81
Yours Truly, Johnny Dollar - 1951-02-03 - 081 - The Monopoly Matter.jpg | 82
Yours Truly, Johnny Dollar - 1951-02-10 - 082 - The Lloyd Hammerly Matter.jpg | 83
Yours Truly, Johnny Dollar - 1951-02-17 - 083 - The Vivian Fair Matter.jpg | 84
Yours Truly, Johnny Dollar - 1951-02-24 - 084 - The Jarvis Wilder Matter.jpg | 85
Yours Truly, Johnny Dollar - 1951-03-03 - 085 - The Celia Woodstock Matter.jpg | 86
Yours Truly, Johnny Dollar - 1951-03-10 - 086 - The Stanley Springs Matter.jpg | 87
Yours Truly, Johnny Dollar - 1951-03-17 - 087 - The Emil Lovett Matter.jpg | 88
Yours Truly, Johnny Dollar - 1951-03-24 - 088 - The Byron Hayes Matter.jpg | 89
Yours Truly, Johnny Dollar - 1951-04-07 - 090 - The Edward French Matter.jpg | 91
Yours Truly, Johnny Dollar - 1951-04-14 - 091 - The Mickey McQueen Matter.jpg | 92
Yours Truly, Johnny Dollar - 1951-04-21 - 092 - The Willard South Matter.jpg | 93
Yours Truly, Johnny Dollar - 1951-04-28 - 093 - The Month-End Raid Matter.jpg | 94
Yours Truly, Johnny Dollar - 1951-05-05 - 094 - The Virginia Towne Matter.jpg | 95
Yours Truly, Johnny Dollar - 1951-05-12 - 095 - The Marie Meadows Matter.jpg | 96
Yours Truly, Johnny Dollar - 1951-05-19 - 096 - The Jane Doe Matter.jpg | 97
Yours Truly, Johnny Dollar - 1951-05-26 - 097 - The Lillis Bond Matter.jpg | 98
Yours Truly, Johnny Dollar - 1951-06-02 - 098 - The Soderbury, Maine, Matter.jpg | 99
Yours Truly, Johnny Dollar - 1951-06-09 - 099 - The George Farmer Matter.jpg | 100
Yours Truly, Johnny Dollar - 1951-06-16 - 100 - The Arthur Boldrick Matter.jpg | 101
Yours Truly, Johnny Dollar - 1951-06-20 - 101 - The Malcolm Wish, M.D. Matter.jpg | 102
Yours Truly, Johnny Dollar - 1951-06-27 - 102 - The Hatchet House Matter.jpg | 103
Yours Truly, Johnny Dollar - 1951-07-04 - 103 - The Alonzo Chapman Matter.jpg | 104
Yours Truly, Johnny Dollar - 1951-07-11 - 104 - The Fair-Way Matter.jpg | 105
Yours Truly, Johnny Dollar - 1951-07-18 - 105 - The Neal Breer Matter.jpg | 106
Yours Truly, Johnny Dollar - 1951-07-25 - 106 - The Blind Item Matter (last page).jpg | 107
Yours Truly, Johnny Dollar - 1951-08-01 - 107 - The Horace Lockhart Matter.jpg | 108
Yours Truly, Johnny Dollar - 1951-08-08 - 108 - The Morgan Fry Matter.jpg | 109
Yours Truly, Johnny Dollar - 1951-08-15 - 109 - The Lucky Costa Matter.jpg | 110
Yours Truly, Johnny Dollar - 1951-08-22 - 110 - The Cumberland Theft Matter.jpg | 111
Yours Truly, Johnny Dollar - 1951-08-29 - 111 - The Leland Case Matter.jpg | 112
Yours Truly, Johnny Dollar - 1951-09-12 - 112 - The Rum Barrel Matter.jpg | 113
Yours Truly, Johnny Dollar - 1951-09-19 - 113 - The Cuban Jewel Matter.jpg | 114
Yours Truly, Johnny Dollar - 1951-09-26 - 114 - The Protection Matter.jpg | 115
Yours Truly, Johnny Dollar - 1951-10-06 - 115 - The Douglas Taylor Matter.jpg | 116
Yours Truly, Johnny Dollar - 1951-10-13 - 116 - The Millard Ward Matter.jpg | 117
Yours Truly, Johnny Dollar - 1951-10-20 - 117 - The Janet Abbe Matter.jpg | 118
Yours Truly, Johnny Dollar - 1951-10-27 - 118 - The Tolhurst Theft Matter.jpg | 119
Yours Truly, Johnny Dollar - 1951-11-03 - 119 - The Hannibal Murphy Matter.jpg | 120
Yours Truly, Johnny Dollar - 1951-11-10 - 120 - The Birdy Baskerville Matter.jpg | 121
Yours Truly, Johnny Dollar - 1951-11-17 - 121 - The Merrill Kent Matter.jpg | 122
Yours Truly, Johnny Dollar - 1951-12-08 - 122 - The Youngstown Credit Group Matter.jpg | 123
Yours Truly, Johnny Dollar - 1951-12-15 - 123 - The Paul Barberis Matter.jpg | 124
Yours Truly, Johnny Dollar - 1951-12-22 - 124 - The Maynard Collins Matter.jpg | 125
Yours Truly, Johnny Dollar - 1951-12-29 - 125 - The Alma Scott Matter.jpg | 126
Yours Truly, Johnny Dollar - 1952-01-05 - 126 - The Glen English Matter.jpg | 127
Yours Truly, Johnny Dollar - 1952-01-12 - 127 - The Baxter Matter.jpg | 128
Yours Truly, Johnny Dollar - 1952-07-02 - 128 - The Amelia Harwell Matter.jpg | 129
Yours Truly, Johnny Dollar - 1952-07-16 - 130 - The Henry Page Matter.jpg | 130
Yours Truly, Johnny Dollar - 1952-07-30 - 132 - The New Bedford Morgue Matter.jpg | 131
Yours Truly, Johnny Dollar - 1952-08-06 - 133 - The Sidney Mann Matter.jpg | 132
Yours Truly, Johnny Dollar - 1952-08-13 - 134 - The Tom Hickman Matter.jpg | 133
Yours Truly, Johnny Dollar - 1952-08-20 - 135 - The Edith Maxwell Matter.jpg | 134
Yours Truly, Johnny Dollar - 1952-08-27 - 136 - The Yankee Pride Matter.jpg | 135
Yours Truly, Johnny Dollar - 1952-09-03 - 137 - The Montevideo Matter.jpg | 136
Yours Truly, Johnny Dollar - 1952-11-24 - 000 - The Trans-Pacific Matter, Part 1.jpg | 137
Yours Truly, Johnny Dollar - 1952-11-24 - 000 - The Trans-Pacific Matter, Part 2.jpg | 138
Yours Truly, Johnny Dollar - 1952-11-28 - 138 - The Singapore Arson Matter.jpg | 139
Yours Truly, Johnny Dollar - 1952-12-05 - 139 - The James Clayton Matter.jpg | 140
Yours Truly, Johnny Dollar - 1952-12-12 - 140 - The Elliott Champion Matter.jpg | 141
Yours Truly, Johnny Dollar - 1952-12-19 - 141 - The New Cambridge Matter.jpg | 142
Yours Truly, Johnny Dollar - 1952-12-26 - 142 - The Walter Patterson Matter.jpg | 143
Yours Truly, Johnny Dollar - 1953-01-02 - 143 - The Baltimore Matter.jpg | 144
Yours Truly, Johnny Dollar - 1953-01-09 - 144 - The Thelma Ibsen Matter (alternate copy).jpg | -
Yours Truly, Johnny Dollar - 1953-01-09 - 144 - The Thelma Ibsen Matter.jpg | 145
Yours Truly, Johnny Dollar - 1953-01-16 - 145 - The Starlet Matter.jpg | 146
Yours Truly, Johnny Dollar - 1953-01-23 - 146 - The Marigold Matter.jpg | 147
Yours Truly, Johnny Dollar - 1953-01-30 - 147 - The Kay Bellamy Matter.jpg | 148
Yours Truly, Johnny Dollar - 1953-02-06 - 148 - The Chicago Fraud Matter.jpg | 149
Yours Truly, Johnny Dollar - 1953-02-13 - 149 - The Lancer Jewelry Matter.jpg | 150
Yours Truly, Johnny Dollar - 1953-02-20 - 150 - The Latourette Matter.jpg | 151
Yours Truly, Johnny Dollar - 1953-02-27 - 151 - The Underwood Matter.jpg | 152
Yours Truly, Johnny Dollar - 1953-03-06 - 152 - The Jeanne Maxwell Matter.jpg | 153
Yours Truly, Johnny Dollar - 1953-03-10 - 153 - The Birdy Baskerville Matter.jpg | 154
Yours Truly, Johnny Dollar - 1953-03-17 - 154 - The King's Necklace Matter.jpg | 155
Yours Truly, Johnny Dollar - 1953-03-24 - 155 - The Syndicate Matter.jpg | 156
Yours Truly, Johnny Dollar - 1953-03-31 - 156 - The Lester James Matter.jpg | 157
Yours Truly, Johnny Dollar - 1953-04-07 - 157 - The Enoch Arden Matter.jpg | 158
Yours Truly, Johnny Dollar - 1953-04-14 - 158 - The Madison Matter.jpg | 159
Yours Truly, Johnny Dollar - 1953-04-21 - 159 - The Dameron Matter.jpg | 160
Yours Truly, Johnny Dollar - 1953-04-28 - 160 - The San Antonio Matter.jpg | 161
Yours Truly, Johnny Dollar - 1953-05-05 - 161 - The Blackmail Matter.jpg | 162
Yours Truly, Johnny Dollar - 1953-05-12 - 162 - The Rochester Theft Matter.jpg | 163
Yours Truly, Johnny Dollar - 1953-05-19 - 163 - The Emily Braddock Matter.jpg | 164
Yours Truly, Johnny Dollar - 1953-05-26 - 164 - The Brisbane Fraud Matter.jpg | 165
Yours Truly, Johnny Dollar - 1953-06-02 - 165 - The Costain Matter.jpg | 166
Yours Truly, Johnny Dollar - 1953-06-09 - 166 - The Oklahoma Red Matter.jpg | 167
Yours Truly, Johnny Dollar - 1953-06-16 - 167 - The Emil Carter Matter.jpg | 168
Yours Truly, Johnny Dollar - 1953-06-23 - 168 - The Jonathan Bellows Matter.jpg | 169
Yours Truly, Johnny Dollar - 1953-06-30 - 169 - The Jones Matter.jpg | 170
Yours Truly, Johnny Dollar - 1953-07-07 - 170 - The Bishop Blackmail Matter.jpg | 171
Yours Truly, Johnny Dollar - 1953-07-14 - 171 - The Shayne Bombing Matter.jpg | 172
Yours Truly, Johnny Dollar - 1953-07-21 - 172 - The Black Doll Matter.jpg | 173
Yours Truly, Johnny Dollar - 1953-07-28 - 173 - The James Forbes Matter.jpg | 174
Yours Truly, Johnny Dollar - 1953-08-04 - 174 - The Voodoo Matter.jpg | 175
Yours Truly, Johnny Dollar - 1953-08-11 - 175 - The Nancy Shaw Matter.jpg | 176
Yours Truly, Johnny Dollar - 1953-08-18 - 176 - The Kimball Matter.jpg | 177
Yours Truly, Johnny Dollar - 1953-08-18 - 176 - The Kimball Matter (page 2).jpg | -
Yours Truly, Johnny Dollar - 1953-08-25 - 177 - The Nelson Matter.jpg | 178
Yours Truly, Johnny Dollar - 1953-09-01 - 178 - The Stanley Price Matter.jpg | 179
Yours Truly, Johnny Dollar - 1953-09-08 - 179 - The Lester Matson Matter.jpg | 180
Yours Truly, Johnny Dollar - 1953-09-15 - 180 - The Oscar Clark Matter.jpg | 181
Yours Truly, Johnny Dollar - 1953-09-22 - 181 - The William Post Matter.jpg | 182
Yours Truly, Johnny Dollar - 1953-10-06 - 183 - The Alfred Chambers Matter.jpg | 184
Yours Truly, Johnny Dollar - 1953-10-13 - 184 - The Phillip Morey Matter.jpg | 185
Yours Truly, Johnny Dollar - 1953-10-20 - 185 - The Allen Saxton Matter.jpg | 186
Yours Truly, Johnny Dollar - 1953-10-27 - 186 - The Howard Arnold Matter.jpg | 187
Yours Truly, Johnny Dollar - 1953-11-03 - 187 - The Gino Gambona Matter.jpg | 188
Yours Truly, Johnny Dollar - 1953-11-10 - 188 - The Bobby Foster Matter.jpg | 189
Yours Truly, Johnny Dollar - 1953-11-17 - 189 - The Nathan Gayles Matter.jpg | 190
Yours Truly, Johnny Dollar - 1953-11-24 - 190 - The Independent Diamond Traders' Matter.jpg | 191
Yours Truly, Johnny Dollar - 1953-12-01 - 191 - The Monopoly Matter.jpg | 192
Yours Truly, Johnny Dollar - 1953-12-08 - 192 - The Barton Baker Matter.jpg | 193
Yours Truly, Johnny Dollar - 1953-12-15 - 193 - The Milk And Honey Matter.jpg | 194
Yours Truly, Johnny Dollar - 1953-12-22 - 194 - The Rudy Valentine Matter.jpg | 195
Yours Truly, Johnny Dollar - 1953-12-29 - 195 - The Ben Bryson Matter.jpg | 196
Yours Truly, Johnny Dollar - 1954-02-02 - 200 - The Paul Gorrell Matter.jpg | 201
Yours Truly, Johnny Dollar - 1954-02-09 - 201 - The Harpooned Angler Matter.jpg | 202
Yours Truly, Johnny Dollar - 1954-02-23 - 203 - The Classified Killer Matter.jpg | 204
Yours Truly, Johnny Dollar - 1954-03-02 - 204 - The Road-Test Matter.jpg | 205
Yours Truly, Johnny Dollar - 1954-03-09 - 205 - The Terrified Taun Matter.jpg | 206
Yours Truly, Johnny Dollar - 1954-03-16 - 206 - The Berlin Matter.jpg | 207
Yours Truly, Johnny Dollar - 1954-03-23 - 207 - The Piney Corners Matter.jpg | 208
Yours Truly, Johnny Dollar - 1954-03-30 - 208 - The Undried Fiddle Back Matter.jpg | 209
Yours Truly, Johnny Dollar - 1954-04-06 - 209 - The Sulphur And Brimstone Matter.jpg | 210
Yours Truly, Johnny Dollar - 1954-04-13 - 210 - The Magnolia And Honeysuckle Matter.jpg | 211
Yours Truly, Johnny Dollar - 1954-04-20 - 211 - The Nathan Swing Matter.jpg | 212
Yours Truly, Johnny Dollar - 1954-04-27 - 212 - The Frustrated Phoenix Matter.jpg | 213
Yours Truly, Johnny Dollar - 1954-05-04 - 213 - The Dan Frank Matter.jpg | 214
Yours Truly, Johnny Dollar - 1954-05-11 - 214 - The Aromatic Cicatrix Matter.jpg | 215
Yours Truly, Johnny Dollar - 1954-05-18 - 215 - The Bilked Baroness Matter.jpg | 216
Yours Truly, Johnny Dollar - 1954-05-25 - 216 - The Punctilious Firebug Matter.jpg | 217
Yours Truly, Johnny Dollar - 1954-06-01 - 217 - The Temperamental Tote Board Matter.jpg | 218
Yours Truly, Johnny Dollar - 1954-06-08 - 218 - The Sara Dearing Matter.jpg | 219
Yours Truly, Johnny Dollar - 1954-06-15 - 219 - The Paterson Transport Matter.jpg | 220
Yours Truly, Johnny Dollar - 1954-06-22 - 220 - The Arthur Boldrick Matter.jpg | 221
Yours Truly, Johnny Dollar - 1954-06-29 - 221 - The Woodward, Manila Matter.jpg | 222
Yours Truly, Johnny Dollar - 1954-07-06 - 222 - The Jan Brueghel Matter.jpg | 223
Yours Truly, Johnny Dollar - 1954-07-13 - 223 - The Carboniferous Dolomite Matter.jpg | 224
Yours Truly, Johnny Dollar - 1954-07-20 - 224 - The Jeanne Maxwell Matter.jpg | 225
Yours Truly, Johnny Dollar - 1954-07-27 - 225 - The Radioactive Gold Matter.jpg | 226
Yours Truly, Johnny Dollar - 1954-08-03 - 226 - The Hampton Line Matter.jpg | 227
Yours Truly, Johnny Dollar - 1954-08-10 - 227 - The Sarah Martin Matter.jpg | 228
Yours Truly, Johnny Dollar - 1954-09-05 - 228 - The Hamilton Payroll Matter.jpg | 229
Yours Truly, Johnny Dollar - 1954-09-12 - 229 - The Great Bannock Race Matter.jpg | 230
Yours Truly, Johnny Dollar - 1954-09-19 - 230 - The Upjohn Matter.jpg | 231
Yours Truly, Johnny Dollar - 1955-10-03 - 231 - The Macormack Matter, Part 1.jpg | 233
Yours Truly, Johnny Dollar - 1955-10-04 - 232 - The Macormack Matter, Part 2.jpg | 234
Yours Truly, Johnny Dollar - 1955-10-05 - 233 - The Macormack Matter, Part 3.jpg | 235
Yours Truly, Johnny Dollar - 1955-10-06 - 234 - The Macormack Matter, Part 4.jpg | 236
Yours Truly, Johnny Dollar - 1955-10-07 - 235 - The Macormack Matter, Part 5.jpg | 237
Yours Truly, Johnny Dollar - 1955-10-10 - 236 - The Molly K. Matter, Part 1.jpg | 238
Yours Truly, Johnny Dollar - 1955-10-11 - 237 - The Molly K. Matter, Part 2.jpg | 239
Yours Truly, Johnny Dollar - 1955-10-12 - 238 - The Molly K. Matter, Part 3.jpg | 240
Yours Truly, Johnny Dollar - 1955-10-13 - 239 - The Molly K. Matter, Part 4.jpg | 241
Yours Truly, Johnny Dollar - 1955-10-14 - 240 - The Molly K. Matter, Part 5.jpg | 242
Yours Truly, Johnny Dollar - 1955-10-17 - 241 - The Chesapeake Fraud Matter, Part 1.jpg | 243
Yours Truly, Johnny Dollar - 1955-10-18 - 242 - The Chesapeake Fraud Matter, Part 2.jpg | 244
Yours Truly, Johnny Dollar - 1955-10-19 - 243 - The Chesapeake Fraud Matter, Part 3.jpg | 245
Yours Truly, Johnny Dollar - 1955-10-20 - 244 - The Chesapeake Fraud Matter, Part 4.jpg | 246
Yours Truly, Johnny Dollar - 1955-10-21 - 245 - The Chesapeake Fraud Matter, Part 5.jpg | 247
Yours Truly, Johnny Dollar - 1955-10-24 - 246 - The Alvin Summers Matter, Part 1.jpg | 248
Yours Truly, Johnny Dollar - 1955-10-25 - 247 - The Alvin Summers Matter, Part 2.jpg | 249
Yours Truly, Johnny Dollar - 1955-10-26 - 248 - The Alvin Summers Matter, Part 3.jpg | 250
Yours Truly, Johnny Dollar - 1955-10-27 - 249 - The Alvin Summers Matter, Part 4.jpg | 251
Yours Truly, Johnny Dollar - 1955-10-28 - 250 - The Alvin Summers Matter, Part 5.jpg | 252
Yours Truly, Johnny Dollar - 1955-10-31 - 251 - The Valentine Matter, Part 1.jpg | 253
Yours Truly, Johnny Dollar - 1955-11-01 - 252 - The Valentine Matter, Part 2.jpg | 254
Yours Truly, Johnny Dollar - 1955-11-02 - 253 - The Valentine Matter, Part 3.jpg | 255
Yours Truly, Johnny Dollar - 1955-11-03 - 254 - The Valentine Matter, Part 4.jpg | 256
Yours Truly, Johnny Dollar - 1955-11-04 - 255 - The Valentine Matter, Part 5.jpg | 257
Yours Truly, Johnny Dollar - 1955-11-07 - 256 - The Lorko Diamonds Matter, Part 1.jpg | 258
Yours Truly, Johnny Dollar - 1955-11-08 - 257 - The Lorko Diamonds Matter, Part 2.jpg | 259
Yours Truly, Johnny Dollar - 1955-11-09 - 258 - The Lorko Diamonds Matter, Part 3.jpg | 260
Yours Truly, Johnny Dollar - 1955-11-10 - 259 - The Lorko Diamonds Matter, Part 4.jpg | 261
Yours Truly, Johnny Dollar - 1955-11-11 - 260 - The Lorko Diamonds Matter, Part 5.jpg | 262
Yours Truly, Johnny Dollar - 1955-11-14 - 261 - The Broderick Matter, Part 1.jpg | 263
Yours Truly, Johnny Dollar - 1955-11-15 - 262 - The Broderick Matter, Part 2.jpg | 264
Yours Truly, Johnny Dollar - 1955-11-16 - 263 - The Broderick Matter, Part 3.jpg | 265
Yours Truly, Johnny Dollar - 1955-11-17 - 264 - The Broderick Matter, Part 4.jpg | 266
Yours Truly, Johnny Dollar - 1955-11-18 - 265 - The Broderick Matter, Part 5.jpg | 267
Yours Truly, Johnny Dollar - 1955-11-21 - 266 - The Amy Bradshaw Matter, Part 1.jpg | 268
Yours Truly, Johnny Dollar - 1955-11-22 - 267 - The Amy Bradshaw Matter, Part 2.jpg | 269
Yours Truly, Johnny Dollar - 1955-11-23 - 268 - The Amy Bradshaw Matter, Part 3.jpg | 270
Yours Truly, Johnny Dollar - 1955-11-24 - 269 - The Amy Bradshaw Matter, Part 4.jpg | 271
Yours Truly, Johnny Dollar - 1955-11-25 - 270 - The Amy Bradshaw Matter, Part 5.jpg | 272
Yours Truly, Johnny Dollar - 1955-11-28 - 271 - The Henderson Matter, Part 1.jpg | 273
Yours Truly, Johnny Dollar - 1955-11-29 - 272 - The Henderson Matter, Part 2.jpg | 274
Yours Truly, Johnny Dollar - 1955-11-30 - 273 - The Henderson Matter, Part 3.jpg | 275
Yours Truly, Johnny Dollar - 1955-12-01 - 274 - The Henderson Matter, Part 4.jpg | 276
Yours Truly, Johnny Dollar - 1955-12-02 - 275 - The Henderson Matter, Part 5.jpg | 277
Yours Truly, Johnny Dollar - 1955-12-05 - 276 - The Cronin Matter, Part 1.jpg | 278
Yours Truly, Johnny Dollar - 1955-12-06 - 277 - The Cronin Matter, Part 2.jpg | 279
Yours Truly, Johnny Dollar - 1955-12-07 - 278 - The Cronin Matter, Part 3.jpg | 280
Yours Truly, Johnny Dollar - 1955-12-08 - 279 - The Cronin Matter, Part 4.jpg | 281
Yours Truly, Johnny Dollar - 1955-12-09 - 280 - The Cronin Matter, Part 5.jpg | 282
Yours Truly, Johnny Dollar - 1955-12-12 - 281 - The Lansing Fraud Matter, Part 1.jpg | 283
Yours Truly, Johnny Dollar - 1955-12-13 - 282 - The Lansing Fraud Matter, Part 2.jpg | 284
Yours Truly, Johnny Dollar - 1955-12-14 - 283 - The Lansing Fraud Matter, Part 3.jpg | 285
Yours Truly, Johnny Dollar - 1955-12-15 - 284 - The Lansing Fraud Matter, Part 4.jpg | 286
Yours Truly, Johnny Dollar - 1955-12-16 - 285 - The Lansing Fraud Matter, Part 5.jpg | 287
Yours Truly, Johnny Dollar - 1955-12-19 - 286 - The Nick Shurn Matter, Part 1.jpg | 288
Yours Truly, Johnny Dollar - 1955-12-20 - 287 - The Nick Shurn Matter, Part 2.jpg | 289
Yours Truly, Johnny Dollar - 1955-12-21 - 288 - The Nick Shurn Matter, Part 3.jpg | 290
Yours Truly, Johnny Dollar - 1955-12-22 - 289 - The Nick Shurn Matter, Part 4.jpg | 291
Yours Truly, Johnny Dollar - 1955-12-23 - 290 - The Nick Shurn Matter, Part 5.jpg | 292
Yours Truly, Johnny Dollar - 1955-12-26 - 291 - The Forbes Matter, Part 1.jpg | 293
Yours Truly, Johnny Dollar - 1955-12-27 - 292 - The Forbes Matter, Part 2.jpg | 294
Yours Truly, Johnny Dollar - 1955-12-28 - 293 - The Forbes Matter, Part 3.jpg | 295
Yours Truly, Johnny Dollar - 1955-12-29 - 294 - The Forbes Matter, Part 4.jpg | 296
Yours Truly, Johnny Dollar - 1955-12-30 - 295 - The Forbes Matter, Part 5.jpg | 297
Yours Truly, Johnny Dollar - 1956-01-02 - 296 - The Caylin Matter, Part 1.jpg | 298
Yours Truly, Johnny Dollar - 1956-01-03 - 297 - The Caylin Matter, Part 2.jpg | 299
Yours Truly, Johnny Dollar - 1956-01-04 - 298 - The Caylin Matter, Part 3.jpg | 300
Yours Truly, Johnny Dollar - 1956-01-05 - 299 - The Caylin Matter, Part 4.jpg | 301
Yours Truly, Johnny Dollar - 1956-01-06 - 300 - The Caylin Matter, Part 5.jpg | 302
Yours Truly, Johnny Dollar - 1956-01-09 - 301 - The Todd Matter, Part 1.jpg | 303
Yours Truly, Johnny Dollar - 1956-01-10 - 302 - The Todd Matter, Part 2.jpg | 304
Yours Truly, Johnny Dollar - 1956-01-11 - 303 - The Todd Matter, Part 3.jpg | 305
Yours Truly, Johnny Dollar - 1956-01-12 - 304 - The Todd Matter, Part 4.jpg | 306
Yours Truly, Johnny Dollar - 1956-01-13 - 305 - The Todd Matter, Part 5.jpg | 307
Yours Truly, Johnny Dollar - 1956-01-16 - 306 - The Ricardo Amerigo Matter, Part 1.jpg | 308
Yours Truly, Johnny Dollar - 1956-01-17 - 307 - The Ricardo Amerigo Matter, Part 2.jpg | 309
Yours Truly, Johnny Dollar - 1956-01-18 - 308 - The Ricardo Amerigo Matter, Part 3.jpg | 310
Yours Truly, Johnny Dollar - 1956-01-19 - 309 - The Ricardo Amerigo Matter, Part 4.jpg | 311
Yours Truly, Johnny Dollar - 1956-01-20 - 310 - The Ricardo Amerigo Matter, Part 5.jpg | 312
Yours Truly, Johnny Dollar - 1956-01-23 - 311 - The Duke Red Matter, Part 1.jpg | 313
Yours Truly, Johnny Dollar - 1956-01-24 - 312 - The Duke Red Matter, Part 2.jpg | 314
Yours Truly, Johnny Dollar - 1956-01-25 - 313 - The Duke Red Matter, Part 3.jpg | 315
Yours Truly, Johnny Dollar - 1956-01-26 - 314 - The Duke Red Matter, Part 4.jpg | 316
Yours Truly, Johnny Dollar - 1956-01-27 - 315 - The Duke Red Matter, Part 5.jpg | 317
Yours Truly, Johnny Dollar - 1956-01-30 - 316 - The Flight Six Matter, Part 1.jpg | 318
Yours Truly, Johnny Dollar - 1956-01-31 - 317 - The Flight Six Matter, Part 2.jpg | 319
Yours Truly, Johnny Dollar - 1956-02-01 - 318 - The Flight Six Matter, Part 3.jpg | 320
Yours Truly, Johnny Dollar - 1956-02-02 - 319 - The Flight Six Matter, Part 4.jpg | 321
Yours Truly, Johnny Dollar - 1956-02-03 - 320 - The Flight Six Matter, Part 5.jpg | 322
Yours Truly, Johnny Dollar - 1956-02-06 - 321 - The McClain Matter, Part 1.jpg | 323
Yours Truly, Johnny Dollar - 1956-02-07 - 322 - The McClain Matter, Part 2.jpg | 324
Yours Truly, Johnny Dollar - 1956-02-08 - 323 - The McClain Matter, Part 3.jpg | 325
Yours Truly, Johnny Dollar - 1956-02-09 - 324 - The McClain Matter, Part 4.jpg | 326
Yours Truly, Johnny Dollar - 1956-02-10 - 325 - The McClain Matter, Part 5.jpg | 327
Yours Truly, Johnny Dollar - 1956-02-13 - 326 - The Cui Bono Matter, Part 1.jpg | 328
Yours Truly, Johnny Dollar - 1956-02-14 - 327 - The Cui Bono Matter, Part 2.jpg | 329
Yours Truly, Johnny Dollar - 1956-02-15 - 328 - The Cui Bono Matter, Part 3.jpg | 330
Yours Truly, Johnny Dollar - 1956-02-16 - 329 - The Cui Bono Matter, Part 4.jpg | 331
Yours Truly, Johnny Dollar - 1956-02-17 - 330 - The Cui Bono Matter, Part 5.jpg | 332
Yours Truly, Johnny Dollar - 1956-02-20 - 331 - The Bennet Matter, Part 1.jpg | 333
Yours Truly, Johnny Dollar - 1956-02-21 - 332 - The Bennet Matter, Part 2.jpg | 334
Yours Truly, Johnny Dollar - 1956-02-22 - 333 - The Bennet Matter, Part 3.jpg | 335
Yours Truly, Johnny Dollar - 1956-02-23 - 334 - The Bennet Matter, Part 4.jpg | 336
Yours Truly, Johnny Dollar - 1956-02-24 - 335 - The Bennet Matter, Part 5.jpg | 337
Yours Truly, Johnny Dollar - 1956-02-27 - 336 - The Fathom-Five Matter, Part 1.jpg | 338
Yours Truly, Johnny Dollar - 1956-02-28 - 337 - The Fathom-Five Matter, Part 2.jpg | 339
Yours Truly, Johnny Dollar - 1956-02-29 - 338 - The Fathom-Five Matter, Part 3.jpg | 340
Yours Truly, Johnny Dollar - 1956-03-01 - 339 - The Fathom-Five Matter, Part 4.jpg | 341
Yours Truly, Johnny Dollar - 1956-03-02 - 340 - The Fathom-Five Matter, Part 5.jpg | 342
Yours Truly, Johnny Dollar - 1956-03-05 - 341 - The Plantagent Matter, Part 1.jpg | 343
Yours Truly, Johnny Dollar - 1956-03-06 - 342 - The Plantagent Matter, Part 2.jpg | 344
Yours Truly, Johnny Dollar - 1956-03-07 - 343 - The Plantagent Matter, Part 3.jpg | 345
Yours Truly, Johnny Dollar - 1956-03-08 - 344 - The Plantagent Matter, Part 4.jpg | 346
Yours Truly, Johnny Dollar - 1956-03-09 - 345 - The Plantagent Matter, Part 5.jpg | 347
Yours Truly, Johnny Dollar - 1956-03-12 - 346 - The Clinton Matter, Part 1.jpg | 348
Yours Truly, Johnny Dollar - 1956-03-13 - 347 - The Clinton Matter, Part 2.jpg | 349
Yours Truly, Johnny Dollar - 1956-03-14 - 348 - The Clinton Matter, Part 3.jpg | 350
Yours Truly, Johnny Dollar - 1956-03-15 - 349 - The Clinton Matter, Part 4.jpg | 351
Yours Truly, Johnny Dollar - 1956-03-16 - 350 - The Clinton Matter, Part 5.jpg | 352
Yours Truly, Johnny Dollar - 1956-03-19 - 351 - The Jolly Roger Fraud Matter, Part 1.jpg | 353
Yours Truly, Johnny Dollar - 1956-03-20 - 352 - The Jolly Roger Fraud Matter, Part 2.jpg | 354
Yours Truly, Johnny Dollar - 1956-03-21 - 353 - The Jolly Roger Fraud Matter, Part 3.jpg | 355
Yours Truly, Johnny Dollar - 1956-03-22 - 354 - The Jolly Roger Fraud Matter, Part 4.jpg | 356
Yours Truly, Johnny Dollar - 1956-03-23 - 355 - The Jolly Roger Fraud Matter, Part 5.jpg | 357
Yours Truly, Johnny Dollar - 1956-03-26 - 356 - The Lamarr Matter, Part 1.jpg | 358
Yours Truly, Johnny Dollar - 1956-03-27 - 357 - The Lamarr Matter, Part 2.jpg | 359
Yours Truly, Johnny Dollar - 1956-03-28 - 358 - The Lamarr Matter, Part 3.jpg | 360
Yours Truly, Johnny Dollar - 1956-03-29 - 359 - The Lamarr Matter, Part 4.jpg | 361
Yours Truly, Johnny Dollar - 1956-03-30 - 360 - The Lamarr Matter, Part 5.jpg | 362
Yours Truly, Johnny Dollar - 1956-04-02 - 361 - The Salt City Matter, Part 1.jpg | 363
Yours Truly, Johnny Dollar - 1956-04-03 - 362 - The Salt City Matter, Part 2.jpg | 364
Yours Truly, Johnny Dollar - 1956-04-04 - 363 - The Salt City Matter, Part 3.jpg | 365
Yours Truly, Johnny Dollar - 1956-04-05 - 364 - The Salt City Matter, Part 4.jpg | 366
Yours Truly, Johnny Dollar - 1956-04-06 - 365 - The Salt City Matter, Part 5.jpg | 367
Yours Truly, Johnny Dollar - 1956-04-09 - 366 - The Laird Douglas Douglas Of Heatherscote Matter, Part 1.jpg | 368
Yours Truly, Johnny Dollar - 1956-04-10 - 367 - The Laird Douglas Douglas Of Heatherscote Matter, Part 2.jpg | 369
Yours Truly, Johnny Dollar - 1956-04-11 - 368 - The Laird Douglas Douglas Of Heatherscote Matter, Part 3.jpg | 370
Yours Truly, Johnny Dollar - 1956-04-12 - 369 - The Laird Douglas Douglas Of Heatherscote Matter, Part 4.jpg | 371
Yours Truly, Johnny Dollar - 1956-04-13 - 370 - The Laird Douglas Douglas Of Heatherscote Matter, Part 5.jpg | 372
Yours Truly, Johnny Dollar - 1956-04-16 - 371 - The Shepherd Matter, Part 1.jpg | 373
Yours Truly, Johnny Dollar - 1956-04-17 - 372 - The Shepherd Matter, Part 2.jpg | 374
Yours Truly, Johnny Dollar - 1956-04-18 - 373 - The Shepherd Matter, Part 3.jpg | 375
Yours Truly, Johnny Dollar - 1956-04-19 - 374 - The Shepherd Matter, Part 4.jpg | 376
Yours Truly, Johnny Dollar - 1956-04-20 - 375 - The Shepherd Matter, Part 5.jpg | 377
Yours Truly, Johnny Dollar - 1956-04-23 - 376 - The Lonely Hearts Matter, Part 1.jpg | 378
Yours Truly, Johnny Dollar - 1956-04-24 - 377 - The Lonely Hearts Matter, Part 2.jpg | 379
Yours Truly, Johnny Dollar - 1956-04-25 - 378 - The Lonely Hearts Matter, Part 3.jpg | 380
Yours Truly, Johnny Dollar - 1956-04-26 - 379 - The Lonely Hearts Matter, Part 4.jpg | 381
Yours Truly, Johnny Dollar - 1956-04-27 - 380 - The Lonely Hearts Matter, Part 5.jpg | 382
Yours Truly, Johnny Dollar - 1956-04-30 - 381 - The Callicles Matter, Part 1.jpg | 383
Yours Truly, Johnny Dollar - 1956-05-01 - 382 - The Callicles Matter, Part 2.jpg | 384
Yours Truly, Johnny Dollar - 1956-05-02 - 383 - The Callicles Matter, Part 3.jpg | 385
Yours Truly, Johnny Dollar - 1956-05-03 - 384 - The Callicles Matter, Part 4.jpg | 386
Yours Truly, Johnny Dollar - 1956-05-04 - 385 - The Callicles Matter, Part 5.jpg | 387
Yours Truly, Johnny Dollar - 1956-05-07 - 386 - The Silver Blue Matter, Part 1.jpg | 388
Yours Truly, Johnny Dollar - 1956-05-08 - 387 - The Silver Blue Matter, Part 2.jpg | 389
Yours Truly, Johnny Dollar - 1956-05-09 - 388 - The Silver Blue Matter, Part 3.jpg | 390
Yours Truly, Johnny Dollar - 1956-05-10 - 389 - The Silver Blue Matter, Part 4.jpg | 391
Yours Truly, Johnny Dollar - 1956-05-11 - 390 - The Silver Blue Matter, Part 5.jpg | 392
Yours Truly, Johnny Dollar - 1956-05-14 - 391 - The Medium, Well Done Matter, Part 1.jpg | 393
Yours Truly, Johnny Dollar - 1956-05-15 - 392 - The Medium, Well Done Matter, Part 2.jpg | 394
Yours Truly, Johnny Dollar - 1956-05-16 - 393 - The Medium, Well Done Matter, Part 3.jpg | 395
Yours Truly, Johnny Dollar - 1956-05-17 - 394 - The Medium, Well Done Matter, Part 4.jpg | 396
Yours Truly, Johnny Dollar - 1956-05-18 - 395 - The Medium, Well Done Matter, Part 5.jpg | 397
Yours Truly, Johnny Dollar - 1956-05-21 - 396 - The Tears Of Night Matter, Part 1.jpg | 398
Yours Truly, Johnny Dollar - 1956-05-22 - 397 - The Tears Of Night Matter, Part 2.jpg | 399
Yours Truly, Johnny Dollar - 1956-05-23 - 398 - The Tears Of Night Matter, Part 3.jpg | 400
Yours Truly, Johnny Dollar - 1956-05-24 - 399 - The Tears Of Night Matter, Part 4.jpg | 401
Yours Truly, Johnny Dollar - 1956-05-25 - 400 - The Tears Of Night Matter, Part 5.jpg | 402
Yours Truly, Johnny Dollar - 1956-05-28 - 401 - The Reasonable Doubt Matter, Part 1.jpg | 403
Yours Truly, Johnny Dollar - 1956-05-29 - 402 - The Reasonable Doubt Matter, Part 2.jpg | 404
Yours Truly, Johnny Dollar - 1956-05-30 - 403 - The Reasonable Doubt Matter, Part 3.jpg | 405
Yours Truly, Johnny Dollar - 1956-05-31 - 404 - The Reasonable Doubt Matter, Part 4.jpg | 406
Yours Truly, Johnny Dollar - 1956-06-01 - 405 - The Reasonable Doubt Matter, Part 5.jpg | 407
Yours Truly, Johnny Dollar - 1956-06-04 - 406 - The Indestructible Mike Matter, Part 1.jpg | 408
Yours Truly, Johnny Dollar - 1956-06-05 - 407 - The Indestructible Mike Matter, Part 2.jpg | 409
Yours Truly, Johnny Dollar - 1956-06-06 - 408 - The Indestructible Mike Matter, Part 3.jpg | 410
Yours Truly, Johnny Dollar - 1956-06-07 - 409 - The Indestructible Mike Matter, Part 4.jpg | 411
Yours Truly, Johnny Dollar - 1956-06-08 - 410 - The Indestructible Mike Matter, Part 5.jpg | 412
Yours Truly, Johnny Dollar - 1956-06-11 - 411 - The Laughing Matter, Part 1.jpg | 413
Yours Truly, Johnny Dollar - 1956-06-12 - 412 - The Laughing Matter, Part 2.jpg | 414
Yours Truly, Johnny Dollar - 1956-06-13 - 413 - The Laughing Matter, Part 3.jpg | 415
Yours Truly, Johnny Dollar - 1956-06-14 - 414 - The Laughing Matter, Part 4.jpg | 416
Yours Truly, Johnny Dollar - 1956-06-15 - 415 - The Laughing Matter, Part 5.jpg | 417
Yours Truly, Johnny Dollar - 1956-06-18 - 416 - The Pearling Matter, Part 1.jpg | 418
Yours Truly, Johnny Dollar - 1956-06-19 - 417 - The Pearling Matter, Part 2.jpg | 419
Yours Truly, Johnny Dollar - 1956-06-20 - 418 - The Pearling Matter, Part 3.jpg | 420
Yours Truly, Johnny Dollar - 1956-06-21 - 419 - The Pearling Matter, Part 4.jpg | 421
Yours Truly, Johnny Dollar - 1956-06-22 - 420 - The Pearling Matter, Part 5.jpg | 422
Yours Truly, Johnny Dollar - 1956-06-25 - 421 - The Long Shot Matter, Part 1.jpg | 423
Yours Truly, Johnny Dollar - 1956-06-26 - 422 - The Long Shot Matter, Part 2.jpg | 424
Yours Truly, Johnny Dollar - 1956-06-27 - 423 - The Long Shot Matter, Part 3.jpg | 425
Yours Truly, Johnny Dollar - 1956-06-28 - 424 - The Long Shot Matter, Part 4.jpg | 426
Yours Truly, Johnny Dollar - 1956-06-29 - 425 - The Long Shot Matter, Part 5.jpg | 427
Yours Truly, Johnny Dollar - 1956-07-02 - 426 - The Midas Touch Matter, Part 1.jpg | 428
Yours Truly, Johnny Dollar - 1956-07-03 - 427 - The Midas Touch Matter, Part 2.jpg | 429
Yours Truly, Johnny Dollar - 1956-07-04 - 428 - The Midas Touch Matter, Part 3.jpg | 430
Yours Truly, Johnny Dollar - 1956-07-05 - 429 - The Midas Touch Matter, Part 4.jpg | 431
Yours Truly, Johnny Dollar - 1956-07-06 - 430 - The Midas Touch Matter, Part 5.jpg | 432
Yours Truly, Johnny Dollar - 1956-07-09 - 431 - The Shady Lane Matter, Part 1.jpg | 433
Yours Truly, Johnny Dollar - 1956-07-10 - 432 - The Shady Lane Matter, Part 2.jpg | 434
Yours Truly, Johnny Dollar - 1956-07-11 - 433 - The Shady Lane Matter, Part 3.jpg | 435
Yours Truly, Johnny Dollar - 1956-07-12 - 434 - The Shady Lane Matter, Part 4.jpg | 436
Yours Truly, Johnny Dollar - 1956-07-13 - 435 - The Shady Lane Matter, Part 5.jpg | 437
Yours Truly, Johnny Dollar - 1956-07-16 - 436 - The Star Of Capetown Matter, Part 1.jpg | 438
Yours Truly, Johnny Dollar - 1956-07-17 - 437 - The Star Of Capetown Matter, Part 2.jpg | 439
Yours Truly, Johnny Dollar - 1956-07-18 - 438 - The Star Of Capetown Matter, Part 3.jpg | 440
Yours Truly, Johnny Dollar - 1956-07-19 - 439 - The Star Of Capetown Matter, Part 4.jpg | 441
Yours Truly, Johnny Dollar - 1956-07-20 - 440 - The Star Of Capetown Matter, Part 5.jpg | 442
Yours Truly, Johnny Dollar - 1956-07-23 - 441 - The Open Town Matter, Part 1.jpg | 443
Yours Truly, Johnny Dollar - 1956-07-24 - 442 - The Open Town Matter, Part 2.jpg | 444
Yours Truly, Johnny Dollar - 1956-07-25 - 443 - The Open Town Matter, Part 3.jpg | 445
Yours Truly, Johnny Dollar - 1956-07-26 - 444 - The Open Town Matter, Part 4.jpg | 446
Yours Truly, Johnny Dollar - 1956-07-27 - 445 - The Open Town Matter, Part 5.jpg | 447
Yours Truly, Johnny Dollar - 1956-07-30 - 446 - The Sea Legs Matter, Part 1.jpg | 448
Yours Truly, Johnny Dollar - 1956-07-31 - 447 - The Sea Legs Matter, Part 2.jpg | 449
Yours Truly, Johnny Dollar - 1956-08-01 - 448 - The Sea Legs Matter, Part 3.jpg | 450
Yours Truly, Johnny Dollar - 1956-08-02 - 449 - The Sea Legs Matter, Part 4.jpg | 451
Yours Truly, Johnny Dollar - 1956-08-03 - 450 - The Sea Legs Matter, Part 5.jpg | 452
Yours Truly, Johnny Dollar - 1956-08-06 - 451 - The Alder Matter, Part 1.jpg | 453
Yours Truly, Johnny Dollar - 1956-08-07 - 452 - The Alder Matter, Part 2.jpg | 454
Yours Truly, Johnny Dollar - 1956-08-08 - 453 - The Alder Matter, Part 3.jpg | 455
Yours Truly, Johnny Dollar - 1956-08-09 - 454 - The Alder Matter, Part 4.jpg | 456
Yours Truly, Johnny Dollar - 1956-08-10 - 455 - The Alder Matter, Part 5.jpg | 457
Yours Truly, Johnny Dollar - 1956-08-13 - 456 - The Crystal Lake Matter, Part 1.jpg | 458
Yours Truly, Johnny Dollar - 1956-08-14 - 457 - The Crystal Lake Matter, Part 2.jpg | 459
Yours Truly, Johnny Dollar - 1956-08-15 - 458 - The Crystal Lake Matter, Part 3.jpg | 460
Yours Truly, Johnny Dollar - 1956-08-16 - 459 - The Crystal Lake Matter, Part 4.jpg | 461
Yours Truly, Johnny Dollar - 1956-08-17 - 460 - The Crystal Lake Matter, Part 5.jpg | 462
Yours Truly, Johnny Dollar - 1956-08-24 - 461 - The Kranesburg Matter, Part 1.jpg | 463
Yours Truly, Johnny Dollar - 1956-08-27 - 462 - The Kranesburg Matter, Part 2.jpg | 464
Yours Truly, Johnny Dollar - 1956-08-28 - 463 - The Kranesburg Matter, Part 3.jpg | 465
Yours Truly, Johnny Dollar - 1956-08-29 - 464 - The Kranesburg Matter, Part 4.jpg | 466
Yours Truly, Johnny Dollar - 1956-08-30 - 465 - The Kranesburg Matter, Part 5.jpg | 467
Yours Truly, Johnny Dollar - 1956-08-31 - 466 - The Kranesburg Matter.jpg | 468
Yours Truly, Johnny Dollar - 1956-09-03 - 467 - The Curse Of Kamashek Matter, Part 1.jpg | 469
Yours Truly, Johnny Dollar - 1956-09-04 - 468 - The Curse Of Kamashek Matter, Part 2.jpg | 470
Yours Truly, Johnny Dollar - 1956-09-05 - 469 - The Curse Of Kamashek Matter, Part 3.jpg | 471
Yours Truly, Johnny Dollar - 1956-09-07 - 470 - The Curse Of Kamashek Matter, Part 4.jpg | 472
Yours Truly, Johnny Dollar - 1956-09-10 - 472 - The Confidential Matter, Part 1.jpg | 474
Yours Truly, Johnny Dollar - 1956-09-11 - 473 - The Confidential Matter, Part 2.jpg | 475
Yours Truly, Johnny Dollar - 1956-09-12 - 474 - The Confidential Matter, Part 3.jpg | 476
Yours Truly, Johnny Dollar - 1956-09-13 - 475 - The Confidential Matter, Part 4.jpg | 477
Yours Truly, Johnny Dollar - 1956-09-14 - 476 - The Confidential Matter, Part 5.jpg | 478
Yours Truly, Johnny Dollar - 1956-09-17 - 477 - The Imperfect Alibi Matter, Part 1.jpg | 479
Yours Truly, Johnny Dollar - 1956-09-18 - 478 - The Imperfect Alibi Matter, Part 2.jpg | 480
Yours Truly, Johnny Dollar - 1956-09-19 - 479 - The Imperfect Alibi Matter, Part 3.jpg | 481
Yours Truly, Johnny Dollar - 1956-09-20 - 480 - The Imperfect Alibi Matter, Part 4.jpg | 482
Yours Truly, Johnny Dollar - 1956-09-21 - 481 - The Imperfect Alibi Matter, Part 5.jpg | 483
Yours Truly, Johnny Dollar - 1956-09-24 - 482 - The Meg's Palace Matter, Part 1.jpg | 484
Yours Truly, Johnny Dollar - 1956-09-25 - 483 - The Meg's Palace Matter, Part 2.jpg | 485
Yours Truly, Johnny Dollar - 1956-09-26 - 484 - The Meg's Palace Matter, Part 3.jpg | 486
Yours Truly, Johnny Dollar - 1956-09-27 - 485 - The Meg's Palace Matter, Part 4.jpg | 487
Yours Truly, Johnny Dollar - 1956-09-28 - 486 - The Meg's Palace Matter, Part 5.jpg | 488
Yours Truly, Johnny Dollar - 1956-10-01 - 487 - The Picture Postcard Matter, Part 1.jpg | 489
Yours Truly, Johnny Dollar - 1956-10-02 - 488 - The Picture Postcard Matter, Part 2.jpg | 490
Yours Truly, Johnny Dollar - 1956-10-03 - 489 - The Picture Postcard Matter, Part 3.jpg | 491
Yours Truly, Johnny Dollar - 1956-10-04 - 490 - The Picture Postcard Matter, Part 4.jpg | 492
Yours Truly, Johnny Dollar - 1956-10-05 - 491 - The Picture Postcard Matter, Part 5.jpg | 493
Yours Truly, Johnny Dollar - 1956-10-08 - 492 - The Primrose Matter, Part 1.jpg | 494
Yours Truly, Johnny Dollar - 1956-10-09 - 493 - The Primrose Matter, Part 2.jpg | 495
Yours Truly, Johnny Dollar - 1956-10-10 - 494 - The Primrose Matter, Part 3.jpg | 496
Yours Truly, Johnny Dollar - 1956-10-11 - 495 - The Primrose Matter, Part 4.jpg | 497
Yours Truly, Johnny Dollar - 1956-10-12 - 496 - The Primrose Matter, Part 5.jpg | 498
Yours Truly, Johnny Dollar - 1956-10-15 - 497 - The Phantom Chase, Part 1.jpg | 499
Yours Truly, Johnny Dollar - 1956-10-16 - 498 - The Phantom Chase, Part 2.jpg | 500
Yours Truly, Johnny Dollar - 1956-10-17 - 499 - The Phantom Chase, Part 3.jpg | 501
Yours Truly, Johnny Dollar - 1956-10-18 - 500 - The Phantom Chase, Part 4.jpg | 502
Yours Truly, Johnny Dollar - 1956-10-19 - 501 - The Phantom Chase, Part 5.jpg | 503
Yours Truly, Johnny Dollar - 1956-10-22 - 502 - The Phantom Chase, Part 6.jpg | 504
Yours Truly, Johnny Dollar - 1956-10-24 - 503 - The Phantom Chase, Part 7.jpg | 505
Yours Truly, Johnny Dollar - 1956-10-25 - 504 - The Phantom Chase, Part 8.jpg | 506
Yours Truly, Johnny Dollar - 1956-10-26 - 505 - The Phantom Chase, Part 9.jpg | 507
Yours Truly, Johnny Dollar - 1956-10-29 - 506 - The Silent Queen Matter, Part 1.jpg | 508
Yours Truly, Johnny Dollar - 1956-10-30 - 507 - The Silent Queen Matter, Part 2.jpg | 509
Yours Truly, Johnny Dollar - 1956-10-31 - 508 - The Silent Queen Matter, Part 3.jpg | 510
Yours Truly, Johnny Dollar - 1956-11-01 - 509 - The Silent Queen Matter, Part 4.jpg | 511
Yours Truly, Johnny Dollar - 1956-11-02 - 510 - The Silent Queen Matter, Part 5.jpg | 512
Yours Truly, Johnny Dollar - 1956-11-04 - 511 - The Markham Matter.jpg | 514
Yours Truly, Johnny Dollar - 1956-11-11 - 512 - The Big Scoop Matter.jpg | 513
Yours Truly, Johnny Dollar - 1956-11-25 - 513 - The Royal Street Matter.jpg | 515
Yours Truly, Johnny Dollar - 1956-12-02 - 514 - The Burning Carr Matter.jpg | 516
Yours Truly, Johnny Dollar - 1956-12-16 - 515 - The Rasmussen Matter.jpg | 517
Yours Truly, Johnny Dollar - 1956-12-23 - 516 - The Missing Mouse Matter.jpg | 518
Yours Truly, Johnny Dollar - 1956-12-30 - 517 - The Squared Circle Matter.jpg | 519
Yours Truly, Johnny Dollar - 1957-01-06 - 518 - The Ellen Dear Matter.jpg | 520
Yours Truly, Johnny Dollar - 1957-01-13 - 519 - The Desalles Matter.jpg | 521
Yours Truly, Johnny Dollar - 1957-01-20 - 520 - The Blooming Blossom Matter.jpg | 522
Yours Truly, Johnny Dollar - 1957-01-27 - 521 - The Mad Hatter Matter.jpg | 523
Yours Truly, Johnny Dollar - 1957-01-29 - 000 - The Ellen Dear Matter ("Audition").jpg | -
Yours Truly, Johnny Dollar - 1957-02-03 - 522 - The Kirbey Will Matter.jpg | 524
Yours Truly, Johnny Dollar - 1957-02-10 - 523 - The Templeton Matter.jpg | 525
Yours Truly, Johnny Dollar - 1957-02-17 - 524 - The Golden Touch Matter.jpg | 526
Yours Truly, Johnny Dollar - 1957-03-03 - 525 - The Meek Memorial Matter.jpg | 527
Yours Truly, Johnny Dollar - 1957-03-10 - 526 - The Suntan Oil Matter.jpg | 528
Yours Truly, Johnny Dollar - 1957-03-17 - 527 - The Clever Chemist Matter.jpg | 529
Yours Truly, Johnny Dollar - 1957-03-24 - 528 - The Hollywood Matter.jpg | 530
Yours Truly, Johnny Dollar - 1957-04-14 - 530 - The Ming Toy Murphy Matter.jpg | 532
Yours Truly, Johnny Dollar - 1957-04-21 - 531 - The Marley K. Matter.jpg | 533
Yours Truly, Johnny Dollar - 1957-04-28 - 532 - The Melancholy Memory Matter.jpg | 534
Yours Truly, Johnny Dollar - 1957-05-05 - 533 - The Peerless Fire Matter.jpg | 535
Yours Truly, Johnny Dollar - 1957-05-12 - 534 - The Glacier Ghost Matter.jpg | 536
Yours Truly, Johnny Dollar - 1957-05-26 - 536 - The Wayward Truck Matter.jpg | 538
Yours Truly, Johnny Dollar - 1957-06-02 - 537 - The Loss Of Memory Matter.jpg | 539
Yours Truly, Johnny Dollar - 1957-06-09 - 538 - The Mason-Dixon Mismatch Matter.jpg | 540
Yours Truly, Johnny Dollar - 1957-06-23 - 540 - The Parley Barron Matter.jpg | 542
Yours Truly, Johnny Dollar - 1957-06-30 - 541 - The Funny Money Matter.jpg | 543
Yours Truly, Johnny Dollar - 1957-07-07 - 542 - The Felicity Feline Matter.jpg | 544
Yours Truly, Johnny Dollar - 1957-07-14 - 543 - The Heatherstone Players Matter.jpg | 545
Yours Truly, Johnny Dollar - 1957-07-21 - 544 - The Yours Truly Matter.jpg | 546
Yours Truly, Johnny Dollar - 1957-07-28 - 545 - The Confederate Coinage Matter.jpg | 547
Yours Truly, Johnny Dollar - 1957-08-04 - 546 - The Wayward Widow Matter.jpg | 548
Yours Truly, Johnny Dollar - 1957-08-11 - 547 - The Killer's Brand Matter.jpg | 549
Yours Truly, Johnny Dollar - 1957-08-18 - 548 - The Winnipesaukee Wonder Matter.jpg | 550
Yours Truly, Johnny Dollar - 1957-08-25 - 549 - The Smoky Sleeper Matter.jpg | 551
Yours Truly, Johnny Dollar - 1957-09-01 - 550 - The Poor Little Rich Girl Matter.jpg | 552
Yours Truly, Johnny Dollar - 1957-09-08 - 551 - The Charmona Matter.jpg | 553
Yours Truly, Johnny Dollar - 1957-09-15 - 552 - The J. P. D. Matter.jpg | 554
Yours Truly, Johnny Dollar - 1957-09-22 - 553 - The Ideal Vacation Matter.jpg | 555
Yours Truly, Johnny Dollar - 1957-09-29 - 554 - The Doubtful Diary Matter.jpg | 556
Yours Truly, Johnny Dollar - 1957-10-06 - 555 - The Bum Steer Matter.jpg | 557
Yours Truly, Johnny Dollar - 1957-10-13 - 556 - The Silver Belle Matter.jpg | 558
Yours Truly, Johnny Dollar - 1957-10-20 - 557 - The Mary Grace Matter.jpg | 559
Yours Truly, Johnny Dollar - 1957-10-27 - 558 - The Three Sisters Matter.jpg | 560
Yours Truly, Johnny Dollar - 1957-11-03 - 559 - The Model Picture Matter.jpg | 561
Yours Truly, Johnny Dollar - 1957-11-10 - 560 - The Alkalai Mike Matter.jpg | 562
Yours Truly, Johnny Dollar - 1957-11-17 - 561 - The Shy Beneficiary Matter.jpg | 563
Yours Truly, Johnny Dollar - 1957-11-24 - 562 - The Hope To Die Matter.jpg | 564
Yours Truly, Johnny Dollar - 1957-12-01 - 563 - The Sunny Dream Matter.jpg | 565
Yours Truly, Johnny Dollar - 1957-12-08 - 564 - The Hapless Hunter Matter.jpg | 566
Yours Truly, Johnny Dollar - 1957-12-15 - 565 - The Happy Family Matter.jpg | 567
Yours Truly, Johnny Dollar - 1957-12-22 - 566 - The Carmen Kringle Matter.jpg | 568
Yours Truly, Johnny Dollar - 1957-12-29 - 567 - The Latin Lovely Matter.jpg | 569
Yours Truly, Johnny Dollar - 1958-01-05 - 568 - The Ingenuous Jeweler Matter.jpg | 570
Yours Truly, Johnny Dollar - 1958-01-12 - 569 - The Boron 112 Matter.jpg | 571
Yours Truly, Johnny Dollar - 1958-01-19 - 570 - The Eleven O'Clock Matter.jpg | 572
Yours Truly, Johnny Dollar - 1958-01-26 - 571 - The Fire In Paradise Matter.jpg | 573
Yours Truly, Johnny Dollar - 1958-02-02 - 572 - The Price Of Fame Matter.jpg | 574
Yours Truly, Johnny Dollar - 1958-02-09 - 573 - The Sick Chick Matter.jpg | 575
Yours Truly, Johnny Dollar - 1958-02-16 - 574 - The Time And Tide Matter.jpg | 576
Yours Truly, Johnny Dollar - 1958-02-23 - 575 - The Durango Laramie Matter.jpg | 577
Yours Truly, Johnny Dollar - 1958-03-02 - 576 - The Diamond Dilemma Matter.jpg | 578
Yours Truly, Johnny Dollar - 1958-03-09 - 577 - The Wayward Moth Matter.jpg | 579
Yours Truly, Johnny Dollar - 1958-03-16 - 578 - The Salkoff Sequel Matter.jpg | 580
Yours Truly, Johnny Dollar - 1958-03-23 - 579 - The Denver Disbursal Matter.jpg | 581
Yours Truly, Johnny Dollar - 1958-03-30 - 580 - The Killer's List Matter.jpg | 582
Yours Truly, Johnny Dollar - 1958-04-06 - 581 - The Eastern Western Matter.jpg | 583
Yours Truly, Johnny Dollar - 1958-04-13 - 582 - The Wayward Money Matter.jpg | 584
Yours Truly, Johnny Dollar - 1958-04-20 - 583 - The Wayward Trout Matter.jpg | 585
Yours Truly, Johnny Dollar - 1958-04-27 - 584 - The Village Of Virtue Matter.jpg | 586
Yours Truly, Johnny Dollar - 1958-05-04 - 585 - The Carson Arson Matter.jpg | 587
Yours Truly, Johnny Dollar - 1958-05-11 - 586 - The Rolling Stone Matter.jpg | 588
Yours Truly, Johnny Dollar - 1958-05-18 - 587 - The Ghost To Ghost Matter.jpg | 589
Yours Truly, Johnny Dollar - 1958-05-25 - 588 - The Midnite Sun Matter.jpg | 590
Yours Truly, Johnny Dollar - 1958-06-01 - 589 - The Froward Fisherman Matter.jpg | 591
Yours Truly, Johnny Dollar - 1958-06-08 - 590 - The Wayward River Matter.jpg | 592
Yours Truly, Johnny Dollar - 1958-06-15 - 591 - The Delectable Damsel Matter.jpg | 593
Yours Truly, Johnny Dollar - 1958-06-22 - 592 - The Virtuous Mobster Matter.jpg | 594
Yours Truly, Johnny Dollar - 1958-06-29 - 593 - The Ugly Pattern Matter.jpg | 595
Yours Truly, Johnny Dollar - 1958-07-06 - 594 - The Blinker Matter.jpg | 596
Yours Truly, Johnny Dollar - 1958-07-13 - 595 - The Mohave Red Matter.jpg | 597
Yours Truly, Johnny Dollar - 1958-07-20 - 596 - The Mohave Red Sequel Matter.jpg | 598
Yours Truly, Johnny Dollar - 1958-07-27 - 597 - The Wayward Killer Matter.jpg | 599
Yours Truly, Johnny Dollar - 1958-08-03 - 598 - The Lucky 4 Matter.jpg | 600
Yours Truly, Johnny Dollar - 1958-08-10 - 599 - The Two Faced Matter.jpg | 601
Yours Truly, Johnny Dollar - 1958-08-24 - 600 - The Noxious Needle Matter.jpg | 602
Yours Truly, Johnny Dollar - 1958-08-31 - 601 - The Limping Liability Matter.jpg | 603
Yours Truly, Johnny Dollar - 1958-09-07 - 602 - The Mailbu Mystery Matter.jpg | 604
Yours Truly, Johnny Dollar - 1958-09-14 - 603 - The Wayward Diamonds Matter.jpg | 605
Yours Truly, Johnny Dollar - 1958-09-21 - 604 - The Johnson Payroll Matter.jpg | 606
Yours Truly, Johnny Dollar - 1958-09-28 - 605 - The Gruesome Spectacle Matter.jpg | 607
Yours Truly, Johnny Dollar - 1958-10-05 - 606 - The Missing Matter Matter.jpg | 608
Yours Truly, Johnny Dollar - 1958-10-12 - 607 - The Impossible Murder Matter.jpg | 609
Yours Truly, Johnny Dollar - 1958-10-19 - 608 - The Monoxide Mystery Matter.jpg | 610
Yours Truly, Johnny Dollar - 1958-10-26 - 609 - The Basking Ridge Matter.jpg | 611
Yours Truly, Johnny Dollar - 1958-11-02 - 610 - The Crater Lake Matter.jpg | 612
Yours Truly, Johnny Dollar - 1958-11-09 - 611 - The Close Shave Matter.jpg | 613
Yours Truly, Johnny Dollar - 1958-11-16 - 612 - The Double Trouble Matter.jpg | 614
Yours Truly, Johnny Dollar - 1958-11-23 - 613 - The One Most Wanted Matter.jpg | 615
Yours Truly, Johnny Dollar - 1958-11-30 - 614 - The Hair Raising Matter.jpg | 616
Yours Truly, Johnny Dollar - 1958-12-14 - 615 - The Allanmee Matter.jpg | 618
Yours Truly, Johnny Dollar - 1958-12-21 - 616 - The Perilous Parley Matter.jpg | 617
Yours Truly, Johnny Dollar - 1958-12-28 - 617 - The Telltale Tracks Matter.jpg | 619
Yours Truly, Johnny Dollar - 1959-01-04 - 618 - The Hollywood Mystery Matter.jpg | 620
Yours Truly, Johnny Dollar - 1959-01-11 - 619 - The Deadly Doubt Matter.jpg | 621
Yours Truly, Johnny Dollar - 1959-01-25 - 621 - The Doting Dowager Matter.jpg | 623
Yours Truly, Johnny Dollar - 1959-02-01 - 622 - The Curley Waters Matter.jpg | 624
Yours Truly, Johnny Dollar - 1959-02-08 - 623 - The Date With Death Matter.jpg | 625
Yours Truly, Johnny Dollar - 1959-02-15 - 624 - The Shankar Diamond Matter.jpg | 626
Yours Truly, Johnny Dollar - 1959-02-22 - 625 - The Blue Madonna Matter.jpg | 627
Yours Truly, Johnny Dollar - 1959-03-01 - 626 - The Clouded Crystal Matter.jpg | 628
Yours Truly, Johnny Dollar - 1959-03-08 - 627 - The Net Of Circumstance Matter.jpg | 629
Yours Truly, Johnny Dollar - 1959-03-15 - 628 - The Baldero Matter.jpg | 630
Yours Truly, Johnny Dollar - 1959-03-22 - 629 - The Lake Mead Mystery Matter.jpg | 631
Yours Truly, Johnny Dollar - 1959-03-29 - 630 - The Jimmy Carter Matter.jpg | 632
Yours Truly, Johnny Dollar - 1959-04-05 - 631 - The Frisco Fire Matter.jpg | 633
Yours Truly, Johnny Dollar - 1959-04-12 - 632 - The Fairweather Friend Matter.jpg | 634
Yours Truly, Johnny Dollar - 1959-04-19 - 633 - The Cautious Celibate Matter.jpg | 635
Yours Truly, Johnny Dollar - 1959-04-26 - 634 - The Winsome Widow Matter.jpg | 636
Yours Truly, Johnny Dollar - 1959-05-03 - 635 - The Negligent Nephew Matter.jpg | 637
Yours Truly, Johnny Dollar - 1959-05-10 - 636 - The Fatal Filet Matter.jpg | 638
Yours Truly, Johnny Dollar - 1959-05-17 - 637 - The Twin Trouble Matter.jpg | 639
Yours Truly, Johnny Dollar - 1959-05-24 - 638 - The Casque Of Death Matter.jpg | 640
Yours Truly, Johnny Dollar - 1959-05-31 - 639 - The Big H Matter.jpg | 641
Yours Truly, Johnny Dollar - 1959-06-07 - 640 - The Wayward Heiress Matter.jpg | 642
Yours Truly, Johnny Dollar - 1959-06-14 - 641 - The Wayward Sculptor Matter.jpg | 643
Yours Truly, Johnny Dollar - 1959-06-21 - 642 - The Life At Steak Matter.jpg | 644
Yours Truly, Johnny Dollar - 1959-06-28 - 643 - The Mei-Ling Buddah Matter.jpg | 645
Yours Truly, Johnny Dollar - 1959-07-05 - 644 - The Only One Butt Matter.jpg | 646
Yours Truly, Johnny Dollar - 1959-07-12 - 645 - The Frantic Fisherman Matter.jpg | 647
Yours Truly, Johnny Dollar - 1959-07-19 - 646 - The Will And A Way Matter.jpg | 648
Yours Truly, Johnny Dollar - 1959-07-26 - 647 - The Bolt Out Of The Blue Matter.jpg | 649
Yours Truly, Johnny Dollar - 1959-08-02 - 648 - The Deadly Chain Matter.jpg | 650
Yours Truly, Johnny Dollar - 1959-08-09 - 649 - The Lost By A Hair Matter.jpg | 651
Yours Truly, Johnny Dollar - 1959-08-16 - 650 - The Night In Paris Matter.jpg | 652
Yours Truly, Johnny Dollar - 1959-08-23 - 651 - The Embarcadero Matter.jpg | 653
Yours Truly, Johnny Dollar - 1959-08-30 - 652 - The Really Gone Matter.jpg | 654
Yours Truly, Johnny Dollar - 1959-09-06 - 653 - The Backfire That Backfired Matter.jpg | 655
Yours Truly, Johnny Dollar - 1959-09-13 - 654 - The Leumas Matter.jpg | 656
Yours Truly, Johnny Dollar - 1959-09-20 - 655 - The Little Man Who Was There Matter.jpg | 657
Yours Truly, Johnny Dollar - 1959-10-04 - 657 - The Buffalo Matter.jpg | 658
Yours Truly, Johnny Dollar - 1959-10-11 - 658 - The Further Buffalo Matter.jpg | 659
Yours Truly, Johnny Dollar - 1959-10-18 - 659 - The Double Identity Matter.jpg | 660
Yours Truly, Johnny Dollar - 1959-10-18 - 660 - The Missing Missile Matter.jpg | 661
Yours Truly, Johnny Dollar - 1959-11-01 - 661 - The Hand Of Providential Matter.jpg | 662
Yours Truly, Johnny Dollar - 1959-11-08 - 662 - The Larson Arson Matter.jpg | 663
Yours Truly, Johnny Dollar - 1959-11-15 - 663 - The Bayou Body Matter.jpg | 664
Yours Truly, Johnny Dollar - 1959-11-22 - 664 - The Fancy Bridgework Matter.jpg | 665
Yours Truly, Johnny Dollar - 1959-11-29 - 665 - The Wrong Man Matter.jpg | 666
Yours Truly, Johnny Dollar - 1959-12-06 - 666 - The Hired Homicide Matter.jpg | 667
Yours Truly, Johnny Dollar - 1959-12-13 - 667 - The Sudden Wealth Matter.jpg | 668
Yours Truly, Johnny Dollar - 1959-12-20 - 668 - The Red Mystery Matter.jpg | 669
Yours Truly, Johnny Dollar - 1959-12-27 - 669 - The Burning Desire Matter.jpg | 670
Yours Truly, Johnny Dollar - 1960-01-03 - 670 - The Hapless Ham Matter.jpg | 671
Yours Truly, Johnny Dollar - 1960-01-10 - 671 - The Unholy Two Matter.jpg | 672
Yours Truly, Johnny Dollar - 1960-01-17 - 672 - The Evaporated Clue Matter.jpg | 673
Yours Truly, Johnny Dollar - 1960-01-24 - 673 - The Nuclear Goof Matter.jpg | 674
Yours Truly, Johnny Dollar - 1960-01-31 - 674 - The Merry Go Round Matter.jpg | 675
Yours Truly, Johnny Dollar - 1960-02-07 - 675 - The Sidewinder Matter.jpg | 676
Yours Truly, Johnny Dollar - 1960-02-14 - 676 - The P. O. Matter.jpg | 677
Yours Truly, Johnny Dollar - 1960-02-21 - 677 - The Alvin's Alfred Matter.jpg | 678
Yours Truly, Johnny Dollar - 1960-02-28 - 678 - The Look Before The Leap Matter.jpg | 679
Yours Truly, Johnny Dollar - 1960-03-13 - 680 - The Deep Down Matter.jpg | 681
Yours Truly, Johnny Dollar - 1960-03-20 - 681 - The Saturday Night Matter.jpg | 682
Yours Truly, Johnny Dollar - 1960-03-27 - 682 - The False Alarm Matter.jpg | 683
Yours Truly, Johnny Dollar - 1960-04-03 - 683 - The Double Exposure Matter.jpg | 684
Yours Truly, Johnny Dollar - 1960-04-17 - 684 - The Deadly Swamp Matter.jpg | 685
Yours Truly, Johnny Dollar - 1960-04-24 - 685 - The Silver Queen Matter.jpg | 686
Yours Truly, Johnny Dollar - 1960-05-01 - 686 - The Fatal Switch Matter.jpg | 687
Yours Truly, Johnny Dollar - 1960-05-08 - 687 - The Phony Phone Matter.jpg | 688
Yours Truly, Johnny Dollar - 1960-05-15 - 688 - The Mystery Gal Matter.jpg | 689
Yours Truly, Johnny Dollar - 1960-05-22 - 689 - The Man Who Waits Matter.jpg | 690
Yours Truly, Johnny Dollar - 1960-05-29 - 690 - The Redrock Matter.jpg | 691
Yours Truly, Johnny Dollar - 1960-06-05 - 691 - The Canned Canary Matter.jpg | 692
Yours Truly, Johnny Dollar - 1960-06-12 - 692 - The Harried Heiress Matter.jpg | 693
Yours Truly, Johnny Dollar - 1960-06-19 - 693 - The Flask Of Death Matter.jpg | 694
Yours Truly, Johnny Dollar - 1960-06-26 - 694 - The Wholly Unexpected Matter.jpg | 695
Yours Truly, Johnny Dollar - 1960-07-03 - 695 - The Collector's Matter.jpg | 696
Yours Truly, Johnny Dollar - 1960-07-17 - 696 - The Back To The Back Matter.jpg | 697
Yours Truly, Johnny Dollar - 1960-07-31 - 697 - The Rhymer Collection Matter.jpg | 698
Yours Truly, Johnny Dollar - 1960-08-07 - 698 - The Magnanimous Matter.jpg | 699
Yours Truly, Johnny Dollar - 1960-08-14 - 699 - The Paradise Lost Matter.jpg | 700
Yours Truly, Johnny Dollar - 1960-08-21 - 700 - The Twisted Twin Matter.jpg | 701
Yours Truly, Johnny Dollar - 1960-08-28 - 701 - The Deadly Debt Matter.jpg | 702
Yours Truly, Johnny Dollar - 1960-09-04 - 702 - The Killer Kin Matter.jpg | 703
Yours Truly, Johnny Dollar - 1960-09-11 - 703 - The Too Much Money Matter.jpg | 704
Yours Truly, Johnny Dollar - 1960-09-18 - 704 - The Real Smokey Matter.jpg | 705
Yours Truly, Johnny Dollar - 1960-09-25 - 705 - The Five Down Matter.jpg | 706
Yours Truly, Johnny Dollar - 1960-10-02 - 706 - The Stope Of Death Matter.jpg | 707
Yours Truly, Johnny Dollar - 1960-10-09 - 707 - The Recompense Matter.jpg | 708
Yours Truly, Johnny Dollar - 1960-10-16 - 708 - The Twins Of Tahoe Matter.jpg | 709
Yours Truly, Johnny Dollar - 1960-10-23 - 709 - The Unworthy Kin Matter.jpg | 710
Yours Truly, Johnny Dollar - 1960-10-30 - 710 - The What Goes Matter.jpg | 711
Yours Truly, Johnny Dollar - 1960-11-06 - 711 - The Super Salesman Matter.jpg | 712
Yours Truly, Johnny Dollar - 1960-11-20 - 713 - The Double Deal Matter.jpg | 714
""".strip().split("\n")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
