import unittest
from agent_logic import run_sales_agent


class FakeModel:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0
    def converse(self, **kwargs):
        self.calls += 1
        return next(self.responses)


def response(content, reason="tool_use"):
    return {"output": {"message": {"role": "assistant", "content": content}},
            "stopReason": reason, "usage": {"inputTokens": 8, "outputTokens": 12}}


class AgentBoundaryTests(unittest.TestCase):
    def test_model_tool_call_reaches_api_and_final_has_authoritative_result(self):
        model = FakeModel([response([{"toolUse": {"toolUseId": "one", "name": "submit_sales_updates", "input": {"proposals": []}}}]),
                           response([{"text": "No supported updates."}], "end_turn")])
        calls = []
        def api(path, body):
            calls.append((path, body))
            return {"result": []} if path.startswith("/exercises") else {"write_status": "rejected", "crm_fields": {}}
        result = run_sales_agent({"transcript": "No facts", "opportunity_id": "demo", "request_id": "request"}, model, api)
        self.assertEqual([x[0] for x in calls], ["/exercises/P01", "/sales"])
        self.assertEqual(result["sales_result"]["write_status"], "rejected")
        self.assertEqual(result["model_calls"], 2)

    def test_unknown_tool_is_never_executed(self):
        model = FakeModel([response([{"toolUse": {"toolUseId": "one", "name": "shell", "input": {}}}]), response([{"text": "done"}], "end_turn")])
        calls = []
        result = run_sales_agent({"transcript": "hello", "opportunity_id": "demo", "request_id": "request"}, model, lambda *args: calls.append(args))
        self.assertEqual(calls, [])
        self.assertEqual(result["status"], "no_valid_tool_result")

    def test_loop_is_bounded_and_second_write_is_not_executed(self):
        tool = {"toolUse": {"toolUseId": "one", "name": "submit_sales_updates", "input": {"proposals": []}}}
        model = FakeModel([response([tool])] * 4)
        calls = []
        def api(path, body):
            calls.append(path)
            return {"result": []} if path.startswith("/exercises") else {"write_status": "rejected"}
        result = run_sales_agent({"transcript": "hello", "opportunity_id": "demo", "request_id": "request"}, model, api)
        self.assertEqual(model.calls, 3)
        self.assertEqual(calls.count("/sales"), 1)
        self.assertEqual(result["status"], "step_limit")

    def test_invalid_input_does_not_reach_model(self):
        model = FakeModel([])
        with self.assertRaises(ValueError):
            run_sales_agent({"transcript": "x" * 10001, "opportunity_id": "demo", "request_id": "request"}, model, None)
        self.assertEqual(model.calls, 0)
