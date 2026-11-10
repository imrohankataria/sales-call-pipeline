"""Reference answers for the explicit practice contracts. Open after an attempt.

All data is synthetic. Standard library only; no paid model or network needed.
These are practice baselines, not production PHI de-identification software.
"""
import inspect
import json
import math
import random
import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def replace_span(note: str, start: int, end: int, label: str) -> str:
    """Replace one original span [start,end); reject invalid offsets."""
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(note):
        raise ValueError("Invalid character span")
    return note[:start] + f"[{label}]" + note[end:]


def accepted_findings(findings: list[dict], threshold: float) -> list[dict]:
    """Valid finding dicts; keep score >= threshold, preserving order/input."""
    return [f for f in findings if f["score"] >= threshold]


def deidentify(note: str, findings: list[dict], threshold: float) -> str:
    """Valid, non-overlapping original spans, end exclusive; no mutation."""
    for f in sorted(accepted_findings(findings, threshold), key=lambda f: f["start"], reverse=True):
        note = replace_span(note, f["start"], f["end"], f["entity_group"])
    return note


def deidentify_overlap(note: str, findings: list[dict], threshold: float) -> str:
    """Merge connected overlapping accepted spans to their union. Label by
    highest score; tied scores use first input occurrence. Adjacent spans stay
    separate. Validate every accepted span. Never mutate input.
    """
    spans = []
    for i, f in enumerate(findings):
        if f["score"] >= threshold:
            replace_span(note, f["start"], f["end"], f["entity_group"])
            spans.append({**f, "index": i})
    merged = []
    for f in sorted(spans, key=lambda f: f["start"]):
        if not merged or f["start"] >= merged[-1]["end"]:
            merged.append(dict(f))
        else:
            m = merged[-1]
            m["end"] = max(m["end"], f["end"])
            if (f["score"], -f["index"]) > (m["score"], -m["index"]):
                m.update(score=f["score"], index=f["index"], entity_group=f["entity_group"])
    for f in reversed(merged):
        note = replace_span(note, f["start"], f["end"], f["entity_group"])
    return note


def redact(text: str) -> str:
    """Practice formats only: ordinary emails; North-American ddd-ddd-dddd
    phones; 13-16 digit contiguous or space-separated cards. Preserve ORD-12345.
    Detection completeness is outside this deliberately bounded exercise.
    """
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL]", text)
    text = re.sub(r"(?<!\w)\d{3}-\d{3}-\d{4}(?!\w)", "[PHONE]", text)
    # Match the entire space-separated digit run before deciding its length.
    # A bounded 13-16 matcher can accidentally mask the suffix of 17 digits.
    def mask_card(match):
        run = match.group()
        return "[CARD]" if 13 <= sum(ch.isdigit() for ch in run) <= 16 else run
    return re.sub(r"(?<!\w)\d(?:[ ]?\d)*(?!\w)", mask_card, text)


def strip_tracking(text: str) -> str:
    """Whitespace-delimited http(s) URLs, optional final period/comma.
    Remove case-insensitive utm_* and fbclid keys. Keep duplicate other keys,
    blank values and fragments; percent encoding may be normalized.
    """
    def clean(match):
        raw = match.group().rstrip(".,")
        suffix = match.group()[len(raw):]
        p = urlsplit(raw)
        params = [(k,v) for k,v in parse_qsl(p.query, keep_blank_values=True)
                  if not k.lower().startswith("utm_") and k.lower() != "fbclid"]
        return urlunsplit((p.scheme,p.netloc,p.path,urlencode(params),p.fragment)) + suffix
    return re.sub(r"https?://[^\s]+", clean, text)


def normalize(doc: str) -> str:
    """Drop full Page X of Y lines; join word-\nword; dedupe normalized
    paragraphs in first-seen order, preserving a blank line between paragraphs.
    """
    doc = re.sub(r"(?im)^[ \t]*Page \d+ of \d+[ \t]*(?:\n|$)", "", doc)
    doc = re.sub(r"(\w)-\n[ \t]*(\w)", r"\1\2", doc)
    seen, output = set(), []
    for paragraph in re.split(r"\n\s*\n", doc):
        paragraph = " ".join(paragraph.split())
        if paragraph and paragraph not in seen:
            output.append(paragraph)
            seen.add(paragraph)
    return "\n\n".join(output)


def clean_messages(msgs: list[dict]) -> list[dict]:
    """Allow system/user/assistant only; strip content, drop empty; at most
    one nonempty system, moved to front. Merge adjacent equal-role turns with
    newline after moving system. Content must be str; no input mutation.
    """
    system, turns = [], []
    for m in msgs:
        if m.get("role") not in {"system", "user", "assistant"} or not isinstance(m.get("content"), str):
            raise ValueError("Invalid message")
        text = m["content"].strip()
        if text:
            (system if m["role"] == "system" else turns).append({"role":m["role"],"content":text})
    if len(system) > 1:
        raise ValueError("Multiple system messages")
    output = system[:]
    for m in turns:
        if output and output[-1]["role"] == m["role"]:
            output[-1]["content"] += "\n" + m["content"]
        else:
            output.append(dict(m))
    return output


def _remove_trailing_commas(text):
    """Remove commas before } or ] outside JSON strings, retaining content."""
    out, quoted, escaped = [], False, False
    for i, ch in enumerate(text):
        if quoted:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                quoted = False
        else:
            if ch == '"':
                quoted = True
            if ch == ',' and text[i+1:].lstrip().startswith(('}', ']')):
                continue
            out.append(ch)
    return ''.join(out)


def parse_output(reply: str, required: set[str]) -> dict:
    """Find first decodable JSON object in prose/fences; allow trailing commas
    outside strings. Require top-level keys; preserve extra keys. Raise
    ValueError on missing keys, no object, or unclosed object. No eval().
    """
    decoder = json.JSONDecoder()
    # Scan only top-level object openings; raw_decode handles nested braces.
    depth, quoted, escaped = 0, False, False
    starts = []
    for i, ch in enumerate(reply):
        if quoted:
            if escaped: escaped = False
            elif ch == '\\': escaped = True
            elif ch == '"': quoted = False
        elif ch == '"' and depth:
            quoted = True
        elif ch == '{':
            if depth == 0: starts.append(i)
            depth += 1
        elif ch == '}' and depth:
            depth -= 1
    for start in starts:
        try:
            result, _ = decoder.raw_decode(_remove_trailing_commas(reply[start:]))
        except json.JSONDecodeError:
            continue
        if not required <= result.keys():
            raise ValueError("Missing required keys")
        return result
    raise ValueError("No valid JSON object")


def chunk(text: str, max_tokens: int, overlap_sentences: int = 1) -> list[str]:
    """Token = whitespace word, not LLM token. Greedy whole-sentence packing;
    .!? followed by whitespace marks boundaries. Oversize sentence -> ValueError.
    Carry up to overlap_sentences from prior chunk, reducing overlap to leave
    space for at least one new sentence. Guarantee forward progress.
    """
    if type(max_tokens) is not int or max_tokens < 1 or type(overlap_sentences) is not int or overlap_sentences < 0:
        raise ValueError("Invalid budget/overlap")
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(text.split())) if text.strip() else []
    lengths = [len(s.split()) for s in sentences]
    if any(n > max_tokens for n in lengths):
        raise ValueError("A sentence exceeds budget")
    result, i, carry = [], 0, []
    while i < len(sentences):
        while carry and sum(lengths[j] for j in carry) + lengths[i] > max_tokens:
            carry.pop(0)
        indices = carry[:]
        size = sum(lengths[j] for j in indices)
        while i < len(sentences) and size + lengths[i] <= max_tokens:
            indices.append(i)
            size += lengths[i]
            i += 1
        result.append(" ".join(sentences[j] for j in indices))
        carry = indices[-overlap_sentences:] if overlap_sentences else []
    return result


def _words(text):
    return set(re.findall(r"\b\w+\b", text.lower()))


def retrieve(query: str, chunks: dict[str,str], k: int = 2) -> list[str]:
    """Score = number of distinct case-insensitive query words in each chunk.
    Drop zero scores; tie by chunk ID ascending. k=0 -> []; negative -> error.
    No stemming: claim and claims differ. Not semantic retrieval or TF-IDF.
    """
    if type(k) is not int or k < 0:
        raise ValueError("Invalid k")
    query_words = _words(query)
    scores = [(len(query_words & _words(text)), id_) for id_,text in chunks.items()]
    return [id_ for score,id_ in sorted(scores,key=lambda x:(-x[0],x[1])) if score > 0][:k]


def build_prompt(system: str, history: list[str], chunks: list[tuple[str,str]], question: str, budget: int) -> str:
    """Whitespace-word budget counts ALL serialized labels and source IDs.
    Format: SYSTEM: text; history entries as-is; [id] text; QUESTION: text.
    Drop oldest history first, then lowest-ranked chunks at list end. Keep
    system+question, else raise ValueError. Do not mutate inputs.
    """
    if type(budget) is not int or budget < 1:
        raise ValueError("Invalid budget")
    turns, sources = list(history), list(chunks)
    def serialize():
        return "\n".join([f"SYSTEM: {system}", *turns,
                          *(f"[{id_}] {text}" for id_,text in sources), f"QUESTION: {question}"])
    while len(serialize().split()) > budget:
        if turns:
            turns.pop(0)
        elif sources:
            sources.pop()
        else:
            raise ValueError("Required text exceeds budget")
    return serialize()


def rag(question: str, docs: dict[str,str], model, budget: int = 80, k: int = 2) -> dict:
    """Assemble a small RAG: normalize->chunk(no overlap, 16 words)->rank->
    budgeted prompt->injected fake model->JSON parse. Chunk IDs doc_id:index.
    Model returns {answer:str,sources:list[str]}; validate cited IDs against
    sources KEPT in prompt. No matches -> abstain WITHOUT calling model.
    An empty citation list for a generated answer is invalid.
    """
    chunks = {f"{id_}:{i}":c for id_,text in docs.items()
              for i,c in enumerate(chunk(normalize(text),16,0))}
    ranked = retrieve(question,chunks,k)
    if not ranked:
        return {"answer":"I don't have supporting evidence.","sources":[]}
    prompt = build_prompt("Use provided evidence. Cite source IDs.",[],[(id_,chunks[id_]) for id_ in ranked],question,budget)
    allowed = {line.split(']',1)[0][1:] for line in prompt.splitlines() if line.startswith('[')}
    if not allowed:
        return {"answer":"I don't have supporting evidence.","sources":[]}
    result = parse_output(model(prompt),{"answer","sources"})
    if (not isinstance(result["answer"],str) or not result["answer"].strip()
        or not isinstance(result["sources"],list) or not result["sources"]
        or any(not isinstance(s,str) or s not in allowed for s in result["sources"])):
        raise ValueError("Invalid answer/citations")
    return result


def contextual_query(turn: str, history: list[dict], rewriter) -> str:
    """Conversation follow-up: injected rewriter receives
    cleaned history and latest user turn, returns standalone search text.
    Reject empty/non-string output. Do not mutate history. This is an API seam,
    not a heuristic that understands language or a guarantee of query fidelity.
    """
    messages = clean_messages([*history,{"role":"user","content":turn}])
    result = rewriter(messages)
    if not isinstance(result,str) or not result.strip():
        raise ValueError("Invalid rewritten query")
    return result.strip()


def combine_results(results: dict[str,dict], required: list[str]) -> dict:
    """Combine named tool outcomes in required order. Return
    facts=[{tool,value}], missing=[tool], complete=bool. Absent/failed tools
    become missing; never invent a deductible value. No concurrency needed.
    """
    facts,missing = [],[]
    for name in required:
        result = results.get(name,{"ok":False})
        if result.get("ok") is True and "result" in result:
            facts.append({"tool":name,"value":result["result"]})
        else:
            missing.append(name)
    return {"facts":facts,"missing":missing,"complete":not missing}


class ToolRegistry:
    """Small typed registry. Exact argument set/types; bool is not int.
    Duplicate names rejected. dispatch returns structured errors, no escaping
    Exception; tool exceptions become 'tool_failed' without exposing details.
    """
    def __init__(self):
        self.tools = {}

    def register(self, name: str, fn, schema: dict[str,type], description: str = ""):
        if name in self.tools:
            raise ValueError("Duplicate tool")
        inspect.signature(fn).bind(**{key:None for key in schema})
        self.tools[name] = (fn,dict(schema),description)

    def dispatch(self, call: dict) -> dict:
        if not isinstance(call,dict) or not isinstance(call.get("name"),str):
            return {"ok":False,"error":"invalid_call"}
        if call["name"] not in self.tools:
            return {"ok":False,"error":"unknown_tool"}
        fn,schema,_ = self.tools[call["name"]]
        args = call.get("args")
        if not isinstance(args,dict) or set(args) != set(schema) or any(type(args[key]) is not typ for key,typ in schema.items()):
            return {"ok":False,"error":"invalid_args"}
        try:
            return {"ok":True,"result":fn(**args)}
        except Exception:
            return {"ok":False,"error":"tool_failed"}


class FakeClock:
    def __init__(self):
        self.t, self.sleeps = 0.0, []
    def now(self):
        return self.t
    def sleep(self,s):
        self.sleeps.append(s)
        self.t += s


def retry(fn, clock, max_attempts=3, base=1.0, jitter=0.0):
    """Practice: retry RuntimeError only, max_attempts includes first call.
    Sleep base*2**i + uniform(0,jitter) between failed attempts, never after last.
    Validation errors propagate immediately; no real sleeping with FakeClock.
    """
    if type(max_attempts) is not int or max_attempts < 1 or base < 0 or jitter < 0:
        raise ValueError("Invalid retry parameters")
    for i in range(max_attempts):
        try:
            return fn()
        except RuntimeError:
            if i+1 == max_attempts:
                raise
            clock.sleep(base * 2**i + random.uniform(0,jitter))


class TokenBucket:
    """Initially full; fake monotonic time; one token per allow(), capped refill."""
    def __init__(self,rate_per_s:float,capacity:int,clock:FakeClock):
        if rate_per_s <= 0 or type(capacity) is not int or capacity < 1:
            raise ValueError("Invalid bucket")
        self.rate,self.capacity,self.clock = rate_per_s,capacity,clock
        self.tokens,self.updated = float(capacity),clock.now()
    def allow(self) -> bool:
        now = self.clock.now()
        self.tokens = min(self.capacity,self.tokens+max(0,now-self.updated)*self.rate)
        self.updated = now
        if self.tokens < 1:
            return False
        self.tokens -= 1
        return True


@dataclass(frozen=True)
class ChunkRecord:
    id: str
    text: str


def make_chunk(id_:str,text:str) -> ChunkRecord:
    """Return an immutable typed chunk record; text must be nonempty after strip."""
    if not text.strip():
        raise ValueError("Empty text")
    return ChunkRecord(id_,text.strip())


def topk(hits:list[dict],k:int) -> list[dict]:
    """Optional heap practice; sort baseline acceptable. Stable ties, no mutation."""
    if type(k) is not int or k < 0:
        raise ValueError("Invalid k")
    return sorted(hits,key=lambda h:h["score"],reverse=True)[:k]


def independent_grid(rows:int,cols:int) -> list[list[int]]:
    """Optional: allocate zeros; changing one cell must not change another row."""
    if rows < 0 or cols < 0:
        raise ValueError("Invalid dimensions")
    return [[0 for _ in range(cols)] for _ in range(rows)]


def parse_basic(reply: str, required: set[str]) -> dict:
    """Strict whole-reply JSON object; required TOP-LEVEL keys; extras retained.
    No prose, fences, trailing-comma repair or model-output guessing.
    """
    try:
        result = json.loads(reply)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError("Reply must be one strict JSON object") from error
    if not isinstance(result, dict) or not required <= result.keys():
        raise ValueError("Expected an object with all required top-level keys")
    return result


def parse_fenced(reply: str, required: set[str]) -> dict:
    """Exactly one json/unlabeled triple-backtick block; strict object inside.
    Surrounding prose allowed; multiple/unclosed fences and repairs rejected.
    """
    if not isinstance(reply, str) or reply.count("```") != 2:
        raise ValueError("Expected exactly one fenced JSON block")
    block = reply.split("```", 2)[1].strip()
    if re.match(r"json(?:\s|$)", block):
        block = block[4:].strip()
    # Independent baseline: an unfinished parse_basic starter cannot block it.
    try:
        result = json.loads(block)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError("Fenced content must be strict JSON") from error
    if not isinstance(result, dict) or not required <= result.keys():
        raise ValueError("Expected an object with all required top-level keys")
    return result


def chunk_basic(text: str, max_tokens: int) -> list[str]:
    """Whitespace-word budget; greedy whole sentences; NO overlap.
    .!? plus whitespace marks boundaries. Oversize sentence -> ValueError.
    """
    if type(max_tokens) is not int or max_tokens < 1:
        raise ValueError("Budget must be a positive integer")
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(text.split())) if text.strip() else []
    output, current, size = [], [], 0
    for sentence in sentences:
        words = len(sentence.split())
        if words > max_tokens:
            raise ValueError("A sentence exceeds the word budget")
        if current and size + words > max_tokens:
            output.append(" ".join(current))
            current, size = [], 0
        current.append(sentence)
        size += words
    if current:
        output.append(" ".join(current))
    return output


def rag_basic(question: str, docs: dict[str, str], model, helpers, budget: int = 80, k: int = 2) -> dict:
    """Score ONLY the assembler; helpers is the explicitly supplied support module.
    normalize -> chunk_basic(16 words) -> retrieve -> build_prompt -> fake model
    -> parse_basic. Reject malformed/empty answer and unsupported kept citations.
    No matches or no evidence fitting budget -> abstain WITHOUT model call.
    """
    chunks = {f"{doc_id}:{index}": text
              for doc_id, doc in docs.items()
              for index, text in enumerate(helpers.chunk_basic(helpers.normalize(doc), 16))}
    ranked = helpers.retrieve(question, chunks, k)
    abstain = {"answer": "I don't have supporting evidence.", "sources": []}
    if not ranked:
        return abstain
    prompt = helpers.build_prompt("Use provided evidence. Cite source IDs.", [],
                                  [(key, chunks[key]) for key in ranked], question, budget)
    allowed = {line.split("]", 1)[0][1:] for line in prompt.splitlines() if line.startswith("[")}
    if not allowed:
        return abstain
    result = helpers.parse_basic(model(prompt), {"answer", "sources"})
    if (not isinstance(result["answer"], str) or not result["answer"].strip()
            or not isinstance(result["sources"], list) or not result["sources"]
            or any(not isinstance(key, str) or key not in allowed for key in result["sources"])):
        raise ValueError("Invalid answer/citations")
    return result


def evaluate_case(expected_facts: dict, actual_facts: dict, expected_tools: list[str], used_tools: list[str]) -> dict:
    """Deterministic structured comparison, NOT free-text truth evaluation.
    Fact keys are strings; compare each top-level value by exact type and value.
    Tool lists are treated as sets. Return sorted discrepancy key/name lists.
    """
    if (not isinstance(expected_facts, dict) or not isinstance(actual_facts, dict)
            or any(not isinstance(key, str) for key in [*expected_facts, *actual_facts])
            or not isinstance(expected_tools, list) or not isinstance(used_tools, list)
            or any(not isinstance(tool, str) for tool in [*expected_tools, *used_tools])):
        raise ValueError("Expected fact dictionaries and lists of tool names")
    expected, actual = set(expected_facts), set(actual_facts)
    shared = expected & actual
    correct = {key for key in shared if type(expected_facts[key]) is type(actual_facts[key])
               and expected_facts[key] == actual_facts[key]}
    result = {"correct_facts": sorted(correct),
              "missing_facts": sorted(expected - actual),
              "wrong_facts": sorted(shared - correct),
              "unsupported_facts": sorted(actual - expected),
              "missing_tools": sorted(set(expected_tools) - set(used_tools)),
              "unexpected_tools": sorted(set(used_tools) - set(expected_tools))}
    result["passed"] = not any(value for key, value in result.items() if key != "correct_facts")
    return result
