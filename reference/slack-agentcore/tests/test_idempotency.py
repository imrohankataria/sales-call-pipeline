import copy
import unittest
from exercise_api import commit_sales

class FakeTable:
    def __init__(self):
        self.row = None
        self.writes = 0
    def get_item(self, **kwargs):
        return {"Item": copy.deepcopy(self.row)} if self.row else {}
    def put_item(self, Item, ConditionExpression):
        assert "attribute_not_exists" in ConditionExpression
        self.row = copy.deepcopy(Item)
        self.writes += 1

class IdempotencyTests(unittest.TestCase):
    def body(self):
        return {"transcript": "The stage is Proposal.", "proposals": [{"field": "stage", "value": "Proposal", "confidence": 0.9,
                 "evidence_quote": "The stage is Proposal."}], "opportunity_id": "test", "request_id": "same"}
    def test_retry_returns_original_decision_even_if_model_confidence_changes(self):
        table = FakeTable()
        body = self.body()
        self.assertEqual(commit_sales(body, table)["write_status"], "written")
        body["proposals"][0]["confidence"] = 0.81
        result = commit_sales(body, table)
        self.assertEqual(result["write_status"], "replayed")
        self.assertEqual(result["accepted"][0]["confidence"], 0.9)
        self.assertEqual(table.writes, 1)
    def test_changed_transcript_with_same_key_is_conflict_and_cannot_write(self):
        table = FakeTable()
        body = self.body()
        commit_sales(body, table)
        body["transcript"] = "The stage is Negotiation."
        self.assertEqual(commit_sales(body, table)["write_status"], "conflict")
        self.assertEqual(table.writes, 1)
    def test_rejected_proposals_create_no_row(self):
        table = FakeTable()
        body = self.body()
        body["proposals"][0]["value"] = "Closed Won"
        self.assertEqual(commit_sales(body, table)["write_status"], "rejected")
        self.assertEqual(table.writes, 0)
