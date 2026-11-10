import copy
import json
import unittest

from exercise_api import handler, run_exercise, validate_sales_updates


class ApiContractTests(unittest.TestCase):
    def test_threshold_is_inclusive_and_input_preserved(self):
        args = {"findings": [{"score": 0.8, "entity_group": "DATE"}, {"score": 0.7, "entity_group": "NAME"}], "threshold": 0.8}
        before = copy.deepcopy(args)
        self.assertEqual(run_exercise("P01", args), [{"score": 0.8, "entity_group": "DATE"}])
        self.assertEqual(args, before)

    def test_grouping_counts_only_accepted_findings(self):
        self.assertEqual(run_exercise("P02", {"findings": [{"score": 0.8, "entity_group": "DATE"}, {"score": 0.9, "entity_group": "DATE"}, {"score": 0.1, "entity_group": "NAME"}], "threshold": 0.8}), {"DATE": 2})

    def test_unknown_drill_is_rejected(self):
        with self.assertRaises(ValueError):
            run_exercise("P99", {})

    def test_arbitrary_executable_callback_is_rejected(self):
        with self.assertRaises(ValueError):
            run_exercise("P08", {"turn": "What about that?", "history": [], "rewriter": "__import__('os').system('echo unsafe')"})

    def test_bool_is_not_an_integer_limit(self):
        with self.assertRaises(ValueError):
            run_exercise("P06", {"query": "vision", "chunks": {"a": "vision"}, "k": True})

    def test_zero_tool_value_is_retained(self):
        self.assertEqual(run_exercise("P09", {"results": {"accumulator": {"ok": True, "result": 0}}, "required": ["accumulator"]}), {"facts": [{"tool": "accumulator", "value": 0}], "missing": [], "complete": True})

    def test_empty_agent_final_terminates(self):
        result = run_exercise("P10", {"actions": [{"final": ""}], "max_steps": 2})
        self.assertEqual(result, {"status": "completed", "answer": "", "history": []})

    def test_failed_pipeline_tool_preserves_successful_evidence(self):
        result = run_exercise("P11", {"request": {"tenant_id": "north", "plan_id": "basic", "question": "What will I pay?"}, "fail_accumulator": True})
        self.assertEqual(result["facts"], {"copay": 25})
        self.assertEqual(result["missing"], ["accumulator"])
        self.assertFalse(result["complete"])

    def test_pipeline_scopes_before_selecting_revision(self):
        rows = [{"tenant_id": "north", "plan_id": "basic", "id": "doc", "text": "Copay", "copay": 25, "revision": 1}, {"tenant_id": "south", "plan_id": "basic", "id": "doc", "text": "Copay", "copay": 99, "revision": 100}, {"tenant_id": "north", "plan_id": "basic", "id": "doc", "text": "Copay", "copay": 20, "revision": 2}]
        result = run_exercise("P12", {"request": {"tenant_id": "north", "plan_id": "basic", "question": "vision benefits"}, "benefits": rows})
        self.assertEqual(result["facts"], {"copay": 20})

    def test_public_api_returns_json_and_validation_status(self):
        event = {"requestContext": {"http": {"method": "POST"}}, "rawPath": "/exercises/P03", "body": json.dumps({"arguments": {"note": "Alice met Bob.", "start": 0, "end": 5, "label": "NAME"}})}
        result = handler(event, None)
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(json.loads(result["body"])["result"], "[NAME] met Bob.")
        event["body"] = "{broken"
        self.assertEqual(handler(event, None)["statusCode"], 400)

    def test_payload_and_work_limits_bound_expensive_requests(self):
        with self.assertRaises(ValueError):
            run_exercise("P27", {"rows": 100000, "cols": 100000})
        with self.assertRaises(ValueError):
            run_exercise("P23", {"failures": 2, "max_attempts": 10000})


class SalesValidationTests(unittest.TestCase):
    transcript = "The renewal date is 2026-12-01. The stage is Proposal. The contract amount is USD 12000."

    def test_trusted_field_pattern_accepts_exact_value(self):
        proposal = {"field": "renewal_date", "value": "2026-12-01", "confidence": 0.8, "evidence_quote": "The renewal date is 2026-12-01."}
        result = validate_sales_updates(self.transcript, [proposal])
        self.assertEqual(result["accepted"], [proposal])
        self.assertEqual(result["rejected"], [])

    def test_high_confidence_unsupported_value_is_rejected(self):
        proposal = {"field": "renewal_date", "value": "2027-01-01", "confidence": 0.99, "evidence_quote": "The renewal date is 2026-12-01."}
        result = validate_sales_updates(self.transcript, [proposal])
        self.assertEqual(result["accepted"], [])
        self.assertEqual(result["rejected"][0]["reason"], "value_not_supported")

    def test_conflicting_source_values_require_review(self):
        proposal = {"field": "renewal_date", "value": "2026-12-01", "confidence": 0.99, "evidence_quote": "The renewal date is 2026-12-01."}
        result = validate_sales_updates(self.transcript + " The renewal date is 2027-01-01.", [proposal])
        self.assertEqual(result["accepted"], [])
        self.assertEqual(result["rejected"][0]["reason"], "ambiguous_source")

    def test_unknown_field_and_negated_evidence_are_rejected(self):
        proposal = {"field": "renewal_date", "value": "2026-12-01", "confidence": 0.99, "evidence_quote": "The renewal date is not 2026-12-01."}
        self.assertEqual(validate_sales_updates(proposal["evidence_quote"], [proposal])["accepted"], [])


if __name__ == "__main__":
    unittest.main()
