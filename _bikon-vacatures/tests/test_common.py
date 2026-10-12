"""Offline tests met verzonnen voorbeeldteksten. Draaien: python -m unittest discover tests"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import collect  # noqa: E402
import common  # noqa: E402


class ScrubPiiTest(unittest.TestCase):
    def scrub(self, text):
        return common.scrub_pii(text)[0]

    def test_email_and_obfuscated_email(self):
        text = "Stuur je cv naar jan.peeters@firma.be of jan [at] firma [dot] be."
        out = self.scrub(text)
        self.assertNotIn("peeters@", out)
        self.assertNotIn("[at]", out)

    def test_belgian_and_international_phones(self):
        for phone in ["02 123 45 67", "0470/12.34.56", "+32 470 12 34 56", "+32 (0)2 123 45 67", "0032 9 123 45 67"]:
            self.assertIn("[telefoon verwijderd]", self.scrub(f"Bel ons op {phone}."), phone)

    def test_keeps_dates_years_and_salaries(self):
        text = "Start op 01.02.2026, budget 2025-2026, loon 4.500 tot 5.500 euro, 40 uur per week."
        self.assertEqual(self.scrub(text), text)

    def test_names_only_in_contact_sentences(self):
        text = "Je werkt met Azure OpenAI en Copilot Studio. Vragen? Contacteer Sarah Janssens via HR."
        out = self.scrub(text)
        self.assertIn("Azure OpenAI", out)
        self.assertIn("Copilot Studio", out)
        self.assertNotIn("Sarah Janssens", out)

    def test_single_name_after_contact_verb(self):
        out = self.scrub("Meer info? Neem contact op met Sarah.")
        self.assertNotIn("Sarah", out)

    def test_name_with_particle_and_title(self):
        out = self.scrub("Votre interlocutrice : Mme Dupont.\nContactpersoon: Pieter van der Berg")
        self.assertNotIn("Dupont", out)
        self.assertNotIn("Berg", out)

    def test_linkedin_profile(self):
        out = self.scrub("Mijn profiel: https://www.linkedin.com/in/jan-peeters-123/")
        self.assertNotIn("jan-peeters", out)


class NormalizeTest(unittest.TestCase):
    def test_same_job_on_two_sources_has_same_key(self):
        a = common.dedup_key("KBC Group NV", "AI Engineer (m/v/x)", "Brussel, BE", "u1")
        b = common.dedup_key("KBC", "AI engineer", "Bruxelles, Région de Bruxelles-Capitale", "u2")
        self.assertEqual(a, b)

    def test_country_only_place_is_empty(self):
        self.assertEqual(common.normalize_place("Belgium"), "")
        self.assertEqual(common.normalize_place("Brussels Metropolitan Area"), "brussels")

    def test_missing_company_falls_back_to_url(self):
        self.assertNotEqual(
            common.dedup_key(None, "AI Engineer", "Gent", "u1"),
            common.dedup_key(None, "AI Engineer", "Gent", "u2"),
        )

    def test_term_in_text(self):
        self.assertTrue(common.term_in_text("AI-assistent", "Je bouwt een AI assistent"))
        self.assertFalse(common.term_in_text("RAG", "drag and drop"))
        self.assertFalse(common.term_in_text("RAG", "rage and storage"))
        self.assertTrue(common.term_in_text("RAG", "RAG-systemen en RAGs"))
        self.assertTrue(common.term_in_text("chatbot", "Onze chatbots en het chatbotteam"))
        self.assertTrue(common.term_in_text("kennisbank", "beheer van kennisbanken"))
        self.assertTrue(common.term_in_text("AI Act", "conform de AI-Act"))
        self.assertFalse(common.term_in_text("AI Act", "AI actions and activities"))


class RecruiterFlagTest(unittest.TestCase):
    def test_known_agency(self):
        self.assertTrue(common.recruiter_flag("Randstad Professionals", "")[0])

    def test_keyword_in_name(self):
        self.assertTrue(common.recruiter_flag("Brainwave Recruitment", "")[0])

    def test_text_cue(self):
        self.assertTrue(common.recruiter_flag("Acme", "Pour l'un de nos clients, nous cherchons...")[0])

    def test_regular_employer(self):
        self.assertEqual(common.recruiter_flag("Belfius Bank", "Wij bouwen een chatbot."), (False, ""))


class DeduplicateTest(unittest.TestCase):
    def test_merges_sources_and_terms_and_keeps_longest_text(self):
        today = collect.date.today().isoformat()
        records = [
            {"bron": "indeed", "zoekterm": "RAG", "titel": "AI Engineer", "bedrijf": "KBC NV",
             "plaats": "Brussel", "datum": today, "url": "a", "beschrijving": "kort", "sector_bron": None},
            {"bron": "linkedin", "zoekterm": "AI engineer", "titel": "AI engineer (m/f/x)", "bedrijf": "KBC",
             "plaats": "Brussels, Brussels Region, Belgium", "datum": today, "url": "b",
             "beschrijving": "veel langere tekst", "sector_bron": None},
            {"bron": "indeed", "zoekterm": "RAG", "titel": "Oud", "bedrijf": "X", "plaats": "Gent",
             "datum": "2000-01-01", "url": "c", "beschrijving": "", "sector_bron": None},
        ]
        jobs, too_old = collect.deduplicate(records, 30)
        self.assertEqual(too_old, 1)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["bron"], "indeed; linkedin")
        self.assertEqual(jobs[0]["zoekterm"], "RAG; AI engineer")
        self.assertEqual(jobs[0]["beschrijving"], "veel langere tekst")


if __name__ == "__main__":
    unittest.main()
