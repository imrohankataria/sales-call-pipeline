"""OBSERVER ONLY: scoped evidence revisions, preserving the baseline contract."""
import copy
import unittest
from pipeline_reference import BenefitService, FixtureTools


class RevisedFixtureTools(FixtureTools):
    def call(self, name, request):
        outcome = super().call(name, request)
        if name != "benefits" or not outcome["ok"]:
            return outcome
        chosen = {}
        for row in outcome["result"]:
            previous = chosen.get(row["id"])
            if previous is None or row.get("revision", 0) > previous.get("revision", 0):
                chosen[row["id"]] = row
        return {"ok": True, "result": list(chosen.values())}
