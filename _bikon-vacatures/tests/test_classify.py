"""Offline tests voor classify.py met een nagemaakte API-client. Geen netwerkverkeer."""

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import classify  # noqa: E402

JOB = {"job_id": "abc", "bedrijf": "Voorbeeldbank", "titel": "AI Engineer", "plaats": "Brussel",
       "bron": "indeed", "beschrijving": "Je bouwt een RAG-chatbot voor onze klantendienst."}
VALID = {"relevant": "ja", "signaaltype": ["bouwen", "bouwen"], "rol_organisatie": "koper",
         "sector": "bank", "gereguleerd": "ja", "score": 4,
         "motivatie": "De bank bouwt een RAG-chatbot voor de klantendienst."}


class FakeClient:
    def __init__(self, text=None, stop_reason="end_turn"):
        content = [SimpleNamespace(type="thinking", thinking="")]
        if text is not None:
            content.append(SimpleNamespace(type="text", text=text))
        self.response = SimpleNamespace(
            content=content, stop_reason=stop_reason, stop_details=None,
            usage=SimpleNamespace(input_tokens=1000, output_tokens=200,
                                  cache_creation_input_tokens=0, cache_read_input_tokens=1500),
        )
        self.messages = SimpleNamespace(create=self.create)
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.response


class ClassifyJobTest(unittest.TestCase):
    def test_valid_answer(self):
        client = FakeClient(json.dumps(VALID))
        result = classify.classify_job(client, JOB)
        self.assertEqual(result["score"], 4)
        self.assertEqual(result["signaaltype"], ["bouwen"])
        self.assertEqual(result["waarschuwingen"], [])
        # 1000 x 0.10 + 1500 x 0.01 + 200 x 0.50 per miljoen
        self.assertAlmostEqual(result["kost_usd"], 0.000215)
        self.assertEqual(client.kwargs["model"], "claude-haiku-5-5")
        self.assertNotIn("temperature", client.kwargs)

    def test_invalid_value_is_rejected(self):
        with self.assertRaises(classify.ClassificationError):
            classify.classify_job(FakeClient(json.dumps({**VALID, "score": 7})), JOB)
        with self.assertRaises(classify.ClassificationError):
            classify.classify_job(FakeClient(json.dumps({**VALID, "sector": "bakkerij"})), JOB)
        with self.assertRaises(classify.ClassificationError):
            classify.classify_job(FakeClient("geen json"), JOB)

    def test_refusal_and_truncation(self):
        with self.assertRaises(classify.ClassificationError):
            classify.classify_job(FakeClient(None, stop_reason="refusal"), JOB)
        with self.assertRaises(classify.ClassificationError):
            classify.classify_job(FakeClient(None, stop_reason="max_tokens"), JOB)

    def test_consistency_warnings(self):
        answer = {**VALID, "relevant": "nee", "score": 4}
        result = classify.classify_job(FakeClient(json.dumps(answer)), JOB)
        self.assertEqual(len(result["waarschuwingen"]), 2)

    def test_prompt_marks_short_adzuna_text(self):
        self.assertIn("500 tekens", classify.job_prompt({**JOB, "bron": "adzuna"}))
        self.assertNotIn("500 tekens", classify.job_prompt({**JOB, "bron": "adzuna; indeed"}))


class SchemaTest(unittest.TestCase):
    def test_schema_uses_only_supported_keywords(self):
        unsupported = {"minimum", "maximum", "minLength", "maxLength", "maxItems", "uniqueItems", "multipleOf"}

        def walk(node):
            if isinstance(node, dict):
                self.assertFalse(unsupported & node.keys(), node)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(classify.SCHEMA)

    def test_schema_matches_validation_model(self):
        self.assertEqual(set(classify.SCHEMA["required"]), set(classify.Classificatie.model_fields))


if __name__ == "__main__":
    unittest.main()
