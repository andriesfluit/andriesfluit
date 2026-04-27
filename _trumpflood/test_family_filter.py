"""Smoke test for the Donald-vs-family Trump filter in comparators.py.

Run from the _trumpflood/ directory:
    python test_family_filter.py
"""
from comparators import contains_donald_trump


CASES = [
    # (title, expected, why)
    ("Donald Trump kondigt nieuwe tarieven aan",          True,  "plain Donald reference"),
    ("Trump dreigt met nieuwe sancties tegen Iran",       True,  "bare 'Trump' = Donald in headlines"),
    ("Trump Tower in New York verkocht voor 500 miljoen", False, "Trump Tower is a building"),
    ("Eric Trump speaks at Republican convention",        False, "the son, not the president"),
    ("Donald Trump Jr. attacks media on Truth Social",    False, "Don Jr., not the president"),
    ("Ivanka Trump opens new fashion line",               False, "the daughter"),
    ("Melania Trump bezoekt kinderziekenhuis",            False, "the first lady, not the president"),
    ("Trump Organization fined $25M in fraud case",       False, "the company"),
    ("Donald Trump met zoon Trump Jr. in Mar-a-Lago",     True,  "mixed: Donald present, family pattern strips out"),
    ("Witte Huis: Trump tekent decreet over migratie",    True,  "Donald via 'Trump' after stripping nothing"),
    ("Barron Trump enrolls at NYU",                       False, "youngest son"),
    ("Lara Trump considers Senate run in North Carolina", False, "daughter-in-law"),
]


def main():
    failures = 0
    for title, expected, why in CASES:
        got = contains_donald_trump(title)
        ok = (got == expected)
        marker = "OK " if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"{marker} expect={expected!s:5} got={got!s:5}  {why!s:50}  {title}")
    print()
    if failures:
        print(f"{failures} failure(s)")
        raise SystemExit(1)
    print(f"All {len(CASES)} cases passed.")


if __name__ == "__main__":
    main()
