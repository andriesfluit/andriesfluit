"""Offline tests voor report.py met verzonnen vacatures."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import report  # noqa: E402


def job(job_id, bedrijf, bron="indeed", zoekterm="RAG", recruiter=False):
    return {"job_id": job_id, "bedrijf": bedrijf, "titel": f"Titel {job_id}", "bron": bron,
            "zoekterm": zoekterm, "url": f"https://x/{job_id}", "datum": "2026-10-01",
            "plaats": "Gent", "recruiter_vlag": recruiter}


def cls(relevant="ja", score=3, signaal=("bouwen",), rol="koper", sector="bank"):
    return {"relevant": relevant, "score": score, "signaaltype": list(signaal), "rol_organisatie": rol,
            "sector": sector, "gereguleerd": "ja", "motivatie": "Omdat de tekst dat zegt."}


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.jobs = [
            job("a", "KBC NV"), job("b", "KBC"), job("c", "KBC Group"),  # drie relevante vacatures
            job("d", "Solo"),  # één vacature met score 5
            job("e", "Randstad", recruiter=True),  # recruiter: niet in de ranking
            job("f", "Ruis", bron="adzuna", zoekterm="chatbot; RAG"),
        ]
        self.classified = {
            "a": cls(score=4), "b": cls(score=3), "c": cls(score=2, signaal=("governance",)),
            "d": cls(score=5), "e": cls(score=5), "f": cls(relevant="nee", score=1, signaal=()),
        }
        self.rows = report.build_rows(self.jobs, self.classified)

    def test_rows_and_flags(self):
        self.assertEqual(len(self.rows), 6)
        by_title = {r["titel"]: r for r in self.rows}
        self.assertEqual(by_title["Titel f"]["tekst_onvolledig"], "ja")
        self.assertEqual(by_title["Titel f"]["zoekterm"], "chatbot, RAG")
        self.assertEqual(by_title["Titel e"]["recruiter_vlag"], "ja")
        self.assertEqual(self.rows[0]["score"], 5)

    def test_more_vacancies_is_a_stronger_signal(self):
        ranking = report.org_ranking(self.rows)
        self.assertEqual([o["naam"] for o in ranking], ["KBC NV", "Solo"])  # 4 + 2 x 0,5 = 5 wint van 5 op aantal
        self.assertEqual(ranking[0]["orgscore"], 5.0)
        self.assertEqual(ranking[0]["aantal"], 3)
        self.assertEqual(ranking[0]["signalen"], "bouwen, governance")
        self.assertEqual(ranking[0]["titels"], ["Titel a", "Titel b"])  # best scorende eerst

    def test_same_title_in_two_places_counts_once(self):
        jobs = [job("x", "Bluecrux"), job("y", "Bluecrux")]
        for j in jobs:
            j["titel"] = "AI Engineer"
        rows = report.build_rows(jobs, {"x": cls(score=3), "y": cls(score=3)})
        org = report.org_ranking(rows)[0]
        self.assertEqual((org["orgscore"], org["aantal"], org["functies"]), (3, 2, 1))
        self.assertEqual(org["titels"], ["AI Engineer"])

    def test_extra_is_capped(self):
        jobs = [job(str(i), "Groot") for i in range(10)]
        rows = report.build_rows(jobs, {str(i): cls(score=3) for i in range(10)})
        self.assertEqual(report.org_ranking(rows)[0]["orgscore"], 3 + report.MAX_EXTRA)

    def test_summary_sections(self):
        summary = report.build_summary(self.rows, report.org_ranking(self.rows), 0)
        for heading in ("## Kern", "per signaaltype", "per sector", "## Top 25", "## Ruis per zoekterm", "## Kanttekeningen"):
            self.assertIn(heading, summary)
        self.assertIn("5 van de 6 unieke vacatures zijn relevant", summary)

    def test_csv_columns_match_the_brief(self):
        self.assertEqual(report.CSV_COLUMNS[:15], [
            "bedrijf", "titel", "bron", "url", "datum", "plaats", "zoekterm", "relevant", "signaaltype",
            "rol_organisatie", "sector", "gereguleerd", "score", "motivatie", "recruiter_vlag",
        ])


if __name__ == "__main__":
    unittest.main()
