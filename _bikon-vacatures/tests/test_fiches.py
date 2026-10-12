"""Offline tests voor fiches.py."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fiches  # noqa: E402


class MatchTest(unittest.TestCase):
    def test_name_variants_match(self):
        self.assertTrue(fiches.matches("Baloise", "Baloise BE"))
        self.assertTrue(fiches.matches("Mutualité chrétienne", "Mutualité chrétienne (MC)"))
        self.assertTrue(fiches.matches("EY", "EY Belgium"))
        self.assertTrue(fiches.matches("Delen Private Bank", "Delen Private Bank NV"))

    def test_no_partial_word_matches(self):
        self.assertFalse(fiches.matches("Mega", "Megabanking Solutions"))
        self.assertFalse(fiches.matches("EY", "Keyrus"))
        self.assertFalse(fiches.matches("Argenta", None))


class SectionTest(unittest.TestCase):
    def test_relevant_texts_and_other_titles(self):
        jobs = [
            {"job_id": "a", "bedrijf": "Argenta", "titel": "AI Engineer", "bron": "indeed", "beschrijving": "x" * 9000},
            {"job_id": "b", "bedrijf": "Argenta Spaarbank", "titel": "Boekhouder", "bron": "adzuna", "beschrijving": "y"},
        ]
        classified = {
            "a": {"relevant": "ja", "score": 5, "signaaltype": ["bouwen"], "rol_organisatie": "koper",
                  "sector": "bank", "gereguleerd": "ja", "motivatie": "RAG bij een bank."},
            "b": {"relevant": "nee", "score": 1, "signaaltype": [], "rol_organisatie": "koper",
                  "sector": "bank", "gereguleerd": "ja", "motivatie": "Geen AI."},
        }
        text = "\n".join(fiches.org_section("Argenta", jobs, classified))
        self.assertIn("Vacatures: 2, waarvan 1 relevant.", text)
        self.assertIn("- Boekhouder", text)
        self.assertIn("## AI Engineer", text)
        self.assertIn("ingekort, 1000 tekens weggelaten", text)


if __name__ == "__main__":
    unittest.main()
