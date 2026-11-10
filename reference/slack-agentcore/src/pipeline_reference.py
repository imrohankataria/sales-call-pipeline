"""OBSERVER ONLY: reference repairs and the identical candidate checks."""
"""Synthetic fixtures and deterministic tools. No network or model account."""
from copy import deepcopy


BENEFITS = [
    {"tenant_id": "south", "plan_id": "basic", "id": "south:basic",
     "text": "A covered vision visit has a 99 dollar copay.", "copay": 99},
    {"tenant_id": "north", "plan_id": "basic", "id": "north:basic",
     "text": "A covered vision visit has a 25 dollar copay.", "copay": 25},
    {"tenant_id": "north", "plan_id": "plus", "id": "north:plus",
     "text": "A covered vision visit has a 15 dollar copay.", "copay": 15},
]
ACCUMULATORS = {
    ("north", "basic"): {"remaining": 0},
    ("north", "plus"): {"remaining": 100},
    ("south", "basic"): {"remaining": 40},
}


class FixtureTools:
    def __init__(self, benefits=None, accumulators=None, fail_accumulator=False):
        self.benefits = deepcopy(BENEFITS if benefits is None else benefits)
        self.accumulators = deepcopy(ACCUMULATORS if accumulators is None else accumulators)
        self.fail_accumulator = fail_accumulator
        self.calls = []

    def call(self, name, request):
        self.calls.append(name)
        if name == "benefits":
            rows = [row for row in self.benefits
                    if row["plan_id"] == request["plan_id"]
                    and row["tenant_id"] == request["tenant_id"]]
            if not rows:
                return {"ok": False, "error": "not_found"}
            return {"ok": True, "result": deepcopy(rows)}
        if name == "accumulator":
            if self.fail_accumulator:
                raise TimeoutError("fixture backend unavailable")
            value = self.accumulators.get((request["tenant_id"], request["plan_id"]))
            if value is None:
                return {"ok": False, "error": "not_found"}
            return {"ok": True, "result": deepcopy(value)}
        return {"ok": False, "error": "unknown_tool"}


"""A fixture planner: explicit vocabulary, no language-understanding claim."""
import re


def plan_tools(question):
    words = set(re.findall(r"\b\w+\b", question.lower()))
    if words & {"cost", "pay", "deductible"}:
        return ["benefits", "accumulator"]
    return ["benefits"]


"""Public service interface. Preserve it while repairing the stated contract."""


class BenefitService:
    def __init__(self, tools=None, planner=plan_tools):
        self.tools = FixtureTools() if tools is None else tools
        self.planner = planner

    def answer(self, request):
        planned = list(self.planner(request["question"]))
        outcomes = {}
        for name in planned:
            try:
                outcomes[name] = self.tools.call(name, request)
            except Exception:
                outcomes[name] = {"ok": False, "error": "tool_failed"}

        facts, sources, missing = {}, [], []
        for name, outcome in outcomes.items():
            if not outcome["ok"]:
                missing.append(name)
                continue
            value = outcome["result"]
            if name == "benefits":
                facts["copay"] = value[0]["copay"]
                sources.extend(row["id"] for row in value)
            elif name == "accumulator":
                if "remaining" in value:
                    facts["remaining"] = value["remaining"]
                else:
                    missing.append(name)
        return {"facts": facts, "sources": sources, "missing": missing,
                "complete": not missing, "outcomes": outcomes}
