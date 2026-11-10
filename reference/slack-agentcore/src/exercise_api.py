"""Bounded JSON adapters for the original practice code and a synthetic CRM.

Callback exercises accept declared fixture values, never executable code.
This is a demo implementation and does not measure learner fluency.
"""
import base64
import copy
import hashlib
import inspect
import json
import math
import os
import re
import time
from dataclasses import asdict
from datetime import date
from typing import Any, get_args, get_origin, get_type_hints

import practice_answers as a
import support
from agent_reference import run_agent
from pipeline_reference import BenefitService, FixtureTools
from revision_reference import RevisedFixtureTools


def summarize_findings(findings: list[dict], threshold: float) -> dict:
    counts = {}
    for finding in a.accepted_findings(findings, threshold):
        group = finding["entity_group"]
        counts[group] = counts.get(group, 0) + 1
    return counts


def rag_adapter(question: str, docs: dict[str, str], model_reply: str, budget: int = 80, k: int = 2) -> dict:
    return a.rag_basic(question, docs, lambda prompt: model_reply, support, budget, k)


def full_rag_adapter(question: str, docs: dict[str, str], model_reply: str, budget: int = 80, k: int = 2) -> dict:
    return a.rag(question, docs, lambda prompt: model_reply, budget, k)


def query_adapter(turn: str, history: list[dict], rewritten_query: str) -> str:
    return a.contextual_query(turn, history, lambda messages: rewritten_query)


def registry_adapter(calls: list[dict], tools: list[str] = None) -> list[dict]:
    registry = a.ToolRegistry()
    allowed = {"add": (lambda x, y: x + y, {"x": int, "y": int}),
               "multiply": (lambda x, y: x * y, {"x": int, "y": int}),
               "echo": (lambda text: text, {"text": str})}
    for name in (tools if tools is not None else ["add", "multiply", "echo"]):
        if name not in allowed:
            raise ValueError("Only declared fixture tools are supported")
        fn, schema = allowed[name]
        registry.register(name, fn, schema)
    return [registry.dispatch(call) for call in calls]


def agent_adapter(actions: list[dict], max_steps: int = 3) -> dict:
    class Registry:
        def dispatch(self, action):
            return registry_adapter([action])[0]
    def model(history):
        if len(history) < len(actions):
            return copy.deepcopy(actions[len(history)])
        return {"name": "unknown", "args": {}}
    return run_agent(model, Registry(), max_steps)


def pipeline_adapter(request: dict, benefits: list[dict] = None, accumulators: list[dict] = None,
                     fail_accumulator: bool = False, revised: bool = False) -> dict:
    if set(request) != {"question", "tenant_id", "plan_id"} or any(type(v) is not str for v in request.values()):
        raise ValueError("request requires string question, tenant_id and plan_id")
    values = None if accumulators is None else {(x["tenant_id"], x["plan_id"]): {"remaining": x["remaining"]} for x in accumulators}
    tools = (RevisedFixtureTools if revised else FixtureTools)(benefits=benefits, accumulators=values, fail_accumulator=fail_accumulator)
    result = BenefitService(tools).answer(request)
    result["tool_calls"] = tools.calls
    return result


def revised_pipeline_adapter(request: dict, benefits: list[dict] = None, accumulators: list[dict] = None,
                             fail_accumulator: bool = False) -> dict:
    return pipeline_adapter(request, benefits, accumulators, fail_accumulator, revised=True)


def retry_adapter(failures: int, max_attempts: int = 3, base: float = 1.0, result: Any = "ok") -> dict:
    calls = 0
    clock = a.FakeClock()
    def operation():
        nonlocal calls
        calls += 1
        if calls <= failures:
            raise RuntimeError("Synthetic transient failure")
        return result
    try:
        value = a.retry(operation, clock, max_attempts, base, 0)
        return {"ok": True, "result": value, "attempts": calls, "sleeps": clock.sleeps}
    except RuntimeError:
        return {"ok": False, "error": "attempts_exhausted", "attempts": calls, "sleeps": clock.sleeps}


def bucket_adapter(rate_per_s: float, capacity: int, advances: list[float]) -> dict:
    clock = a.FakeClock()
    bucket = a.TokenBucket(rate_per_s, capacity, clock)
    decisions = []
    for elapsed in advances:
        if elapsed < 0:
            raise ValueError("Clock advances must be non-negative")
        clock.sleep(elapsed)
        decisions.append(bucket.allow())
    return {"allowed": decisions, "tokens_remaining": bucket.tokens}


def chunk_record_adapter(id_: str, text: str) -> dict:
    return asdict(a.make_chunk(id_, text))


FUNCTIONS = {
    "P01": a.accepted_findings, "P02": summarize_findings, "P03": a.replace_span,
    "P04": a.deidentify, "P05": a.parse_basic, "P06": a.retrieve,
    "P07": rag_adapter, "P08": query_adapter, "P09": a.combine_results,
    "P10": agent_adapter, "P11": pipeline_adapter, "P12": revised_pipeline_adapter,
    "P13": a.deidentify_overlap, "P14": a.redact, "P15": a.strip_tracking,
    "P16": a.normalize, "P17": a.clean_messages, "P18": a.parse_output,
    "P19": a.chunk, "P20": a.build_prompt, "P21": full_rag_adapter,
    "P22": registry_adapter, "P23": retry_adapter, "P24": bucket_adapter,
    "P25": chunk_record_adapter, "P26": a.topk, "P27": a.independent_grid,
    "P28": a.parse_fenced, "P29": a.chunk_basic, "P30": a.evaluate_case,
}


def _bound_json(value, depth=0):
    if depth > 12:
        raise ValueError("JSON nesting exceeds demo limit")
    if isinstance(value, str) and len(value) > 20000:
        raise ValueError("Text exceeds demo limit")
    if isinstance(value, (list, dict)):
        if len(value) > 1000:
            raise ValueError("Collection exceeds demo limit")
        for item in value.values() if isinstance(value, dict) else value:
            _bound_json(item, depth + 1)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Non-finite values are not allowed")
    elif isinstance(value, int) and abs(value) > 10**12:
        raise ValueError("Integer exceeds demo limit")


def _validate_type(value, annotation):
    if value is None or annotation in (Any, inspect.Signature.empty):
        return
    origin = get_origin(annotation)
    typ = origin or annotation
    if typ is float:
        if type(value) not in (int, float):
            raise ValueError("Expected a number")
    elif typ in (int, str, bool, dict, list, set):
        if type(value) is not typ:
            raise ValueError("Expected " + typ.__name__)
    elif typ is tuple and not isinstance(value, (tuple, list)):
        raise ValueError("Expected a JSON pair")
    subtypes = get_args(annotation)
    if subtypes and typ in (list, set):
        for item in value:
            _validate_type(item, subtypes[0])
    if subtypes and typ is dict:
        for key, item in value.items():
            _validate_type(key, subtypes[0]); _validate_type(item, subtypes[1])
    if subtypes and typ is tuple:
        if len(value) != len(subtypes):
            raise ValueError("Invalid pair length")
        for item, sub in zip(value, subtypes):
            _validate_type(item, sub)


def run_exercise(drill_id, arguments):
    if drill_id not in FUNCTIONS or not isinstance(arguments, dict):
        raise ValueError("Unknown drill or invalid arguments")
    _bound_json(arguments)
    args = copy.deepcopy(arguments)
    fn = FUNCTIONS[drill_id]
    if drill_id in {"P05", "P18", "P28"} and "required" in args:
        if not isinstance(args["required"], list) or any(type(x) is not str for x in args["required"]):
            raise ValueError("required must be a list of keys")
        args["required"] = set(args["required"])
    try:
        bound = inspect.signature(fn).bind(**args)
        bound.apply_defaults()
        hints = get_type_hints(fn)
        for key, value in bound.arguments.items():
            _validate_type(value, hints.get(key, inspect.Signature.empty))
        for key, limit in {"k": 50, "max_steps": 5, "max_attempts": 5, "rows": 200,
                           "cols": 200, "capacity": 1000, "budget": 5000,
                           "max_tokens": 5000, "overlap_sentences": 20, "failures": 5}.items():
            if key in bound.arguments and (type(bound.arguments[key]) is not int or bound.arguments[key] > limit):
                raise ValueError(key + " exceeds demo limit or has wrong type")
        if drill_id == "P27" and args["rows"] * args["cols"] > 10000:
            raise ValueError("Grid exceeds demo limit")
        return fn(**bound.arguments)
    except (TypeError, KeyError, AttributeError, IndexError) as error:
        raise ValueError("Arguments do not satisfy this exercise contract") from error


PATTERNS = {
    "renewal_date": r"\brenewal date is\s+(\d{4}-\d{2}-\d{2})\b",
    "stage": r"\bstage is\s+(Discovery|Proposal|Negotiation|Closed Won|Closed Lost)\b",
    "amount": r"\bcontract amount is USD\s+([\d,]+)\b",
}


def validate_sales_updates(transcript, proposals, threshold=0.8):
    if type(transcript) is not str or not isinstance(proposals, list) or len(proposals) > 10:
        raise ValueError("Invalid sales request")
    _bound_json({"transcript": transcript, "proposals": proposals})
    accepted, rejected, seen = [], [], set()
    for proposal in proposals:
        reason = None
        if not isinstance(proposal, dict) or set(proposal) != {"field", "value", "confidence", "evidence_quote"}:
            reason = "invalid_proposal"
        else:
            field, value, quote, confidence = (proposal[k] for k in ["field", "value", "evidence_quote", "confidence"])
            if type(field) is not str or field not in PATTERNS:
                reason = "unsupported_field"
            elif field in seen:
                reason = "duplicate_field"
            elif type(confidence) not in (float, int) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
                reason = "invalid_confidence"
            elif confidence < threshold:
                reason = "below_threshold"
            elif type(quote) is not str or not quote or quote not in transcript:
                reason = "quote_not_in_source"
            else:
                normalize = (lambda v: int(str(v).replace(",", ""))) if field == "amount" else (lambda v: v.lower())
                matches = re.findall(PATTERNS[field], transcript, flags=re.I)
                quoted = re.findall(PATTERNS[field], quote, flags=re.I)
                if not matches or not quoted:
                    reason = "value_not_supported"
                elif len({normalize(v) for v in matches}) != 1:
                    reason = "ambiguous_source"
                elif (field == "amount" and type(value) is not int) or (field != "amount" and type(value) is not str):
                    reason = "invalid_value_type"
                elif normalize(value) != normalize(matches[0]) or normalize(value) != normalize(quoted[0]):
                    reason = "value_not_supported"
                elif field == "renewal_date":
                    try:
                        date.fromisoformat(value)
                    except ValueError:
                        reason = "invalid_date"
        if reason:
            rejected.append({"proposal": copy.deepcopy(proposal), "reason": reason})
        else:
            accepted.append(copy.deepcopy(proposal)); seen.add(proposal["field"])
    return {"accepted": accepted, "rejected": rejected}


def commit_sales(body, table=None):
    import boto3
    from botocore.exceptions import ClientError
    if not isinstance(body, dict) or set(body) != {"transcript", "proposals", "opportunity_id", "request_id"}:
        raise ValueError("Sales body requires transcript, proposals, opportunity_id and request_id")
    for key in ["opportunity_id", "request_id"]:
        if type(body[key]) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", body[key]):
            raise ValueError("Invalid synthetic identifier")
    decision = validate_sales_updates(body["transcript"], body["proposals"])
    # The idempotency key represents the caller's immutable transcript intent.
    # Model wording/confidence may vary on a retry; the first accepted decision wins.
    intent = {"transcript": body["transcript"], "opportunity_id": body["opportunity_id"], "request_id": body["request_id"]}
    digest = hashlib.sha256(json.dumps(intent, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    table = table if table is not None else boto3.resource("dynamodb").Table(os.environ["CRM_TABLE"])
    key = {"opportunity_id": body["opportunity_id"], "event_id": body["request_id"]}
    def previous_result(previous):
        if previous["payload_hash"] != digest:
            return {"error": "idempotency_conflict", "write_status": "conflict"}
        return {**json.loads(previous["decision_json"]), "write_status": "replayed"}
    previous = table.get_item(Key=key, ConsistentRead=True).get("Item")
    if previous:
        return previous_result(previous)
    if not decision["accepted"]:
        return {**decision, "write_status": "rejected", "crm_fields": {}}
    result = {**decision, "write_status": "written", "crm_fields": {p["field"]: p["value"] for p in decision["accepted"]},
              "opportunity_id": body["opportunity_id"], "request_id": body["request_id"]}
    item = {**key,
            "payload_hash": digest, "fields_json": json.dumps({p["field"]: p["value"] for p in decision["accepted"]}),
            "decision_json": json.dumps(result),
            "created_at": int(time.time()), "ttl": int(time.time()) + 86400}
    try:
        table.put_item(Item=item, ConditionExpression="attribute_not_exists(opportunity_id) AND attribute_not_exists(event_id)")
    except ClientError as error:
        if error.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        previous = table.get_item(Key={"opportunity_id": item["opportunity_id"], "event_id": item["event_id"]}, ConsistentRead=True)["Item"]
        return previous_result(previous)
    return result


def _response(status, body):
    return {"statusCode": status, "headers": {"content-type": "application/json", "cache-control": "no-store"},
            "body": json.dumps(body, allow_nan=False)}


def handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "POST")
    path = event.get("rawPath", "/")
    try:
        if method == "GET" and path == "/health":
            return _response(200, {"status": "ok", "drill_count": len(FUNCTIONS)})
        if method == "GET" and path == "/exercises":
            with open(os.path.join(os.path.dirname(__file__), "catalog.json")) as f:
                return _response(200, json.load(f))
        if method == "GET" and path == "/openapi.json":
            with open(os.path.join(os.path.dirname(__file__), "openapi.json")) as f:
                return _response(200, json.load(f))
        raw = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            raw = base64.b64decode(raw).decode()
        if len(raw.encode()) > 128000:
            return _response(413, {"error": "payload_too_large"})
        body = json.loads(raw, parse_constant=lambda x: (_ for _ in ()).throw(ValueError("Non-finite JSON")))
        if method == "POST" and path.startswith("/exercises/"):
            if not isinstance(body, dict) or set(body) != {"arguments"}:
                raise ValueError("Body requires only the arguments object")
            drill_id = path.rsplit("/", 1)[-1]
            return _response(200, {"drill_id": drill_id, "result": run_exercise(drill_id, body["arguments"]), "implementation": "demo_reference"})
        if method == "POST" and path == "/sales":
            result = commit_sales(body)
            return _response(409 if result.get("write_status") == "conflict" else 200, result)
        return _response(404, {"error": "not_found"})
    except (ValueError, TypeError, KeyError, UnicodeError) as error:
        return _response(400, {"error": "invalid_request", "message": str(error)})
    except Exception as error:
        print(json.dumps({"event": "api_error", "error_type": type(error).__name__}))
        return _response(500, {"error": "internal_error"})
