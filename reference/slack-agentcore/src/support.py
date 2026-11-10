"""SUPPLIED tested support for the rag-basic integration drill.

These helpers are fixtures, not Rohan's implementations. check.py rag-basic
passes this module explicitly and scores only exercises.rag_basic. Do not edit
support.py to make your attempt pass. No imports from the spoiler answer key.
"""
import json
import re

def normalize(doc: str) -> str:
    """Drop full Page X of Y lines; join word-
word; dedupe normalized
    paragraphs in first-seen order, preserving a blank line between paragraphs.
    """
    doc = re.sub('(?im)^[ \\t]*Page \\d+ of \\d+[ \\t]*(?:\\n|$)', '', doc)
    doc = re.sub('(\\w)-\\n[ \\t]*(\\w)', '\\1\\2', doc)
    seen, output = (set(), [])
    for paragraph in re.split('\\n\\s*\\n', doc):
        paragraph = ' '.join(paragraph.split())
        if paragraph and paragraph not in seen:
            output.append(paragraph)
            seen.add(paragraph)
    return '\n\n'.join(output)

def _words(text):
    return set(re.findall('\\b\\w+\\b', text.lower()))

def retrieve(query: str, chunks: dict[str, str], k: int=2) -> list[str]:
    """Score = number of distinct case-insensitive query words in each chunk.
    Drop zero scores; tie by chunk ID ascending. k=0 -> []; negative -> error.
    No stemming: claim and claims differ. Not semantic retrieval or TF-IDF.
    """
    if type(k) is not int or k < 0:
        raise ValueError('Invalid k')
    query_words = _words(query)
    scores = [(len(query_words & _words(text)), id_) for id_, text in chunks.items()]
    return [id_ for score, id_ in sorted(scores, key=lambda x: (-x[0], x[1])) if score > 0][:k]

def build_prompt(system: str, history: list[str], chunks: list[tuple[str, str]], question: str, budget: int) -> str:
    """Whitespace-word budget counts ALL serialized labels and source IDs.
    Format: SYSTEM: text; history entries as-is; [id] text; QUESTION: text.
    Drop oldest history first, then lowest-ranked chunks at list end. Keep
    system+question, else raise ValueError. Do not mutate inputs.
    """
    if type(budget) is not int or budget < 1:
        raise ValueError('Invalid budget')
    turns, sources = (list(history), list(chunks))

    def serialize():
        return '\n'.join([f'SYSTEM: {system}', *turns, *(f'[{id_}] {text}' for id_, text in sources), f'QUESTION: {question}'])
    while len(serialize().split()) > budget:
        if turns:
            turns.pop(0)
        elif sources:
            sources.pop()
        else:
            raise ValueError('Required text exceeds budget')
    return serialize()

def parse_basic(reply: str, required: set[str]) -> dict:
    """Strict whole-reply JSON object; required TOP-LEVEL keys; extras retained.
    No prose, fences, trailing-comma repair or model-output guessing.
    """
    try:
        result = json.loads(reply)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError('Reply must be one strict JSON object') from error
    if not isinstance(result, dict) or not required <= result.keys():
        raise ValueError('Expected an object with all required top-level keys')
    return result

def chunk_basic(text: str, max_tokens: int) -> list[str]:
    """Whitespace-word budget; greedy whole sentences; NO overlap.
    .!? plus whitespace marks boundaries. Oversize sentence -> ValueError.
    """
    if type(max_tokens) is not int or max_tokens < 1:
        raise ValueError('Budget must be a positive integer')
    sentences = re.split('(?<=[.!?])\\s+', ' '.join(text.split())) if text.strip() else []
    output, current, size = ([], [], 0)
    for sentence in sentences:
        words = len(sentence.split())
        if words > max_tokens:
            raise ValueError('A sentence exceeds the word budget')
        if current and size + words > max_tokens:
            output.append(' '.join(current))
            current, size = ([], 0)
        current.append(sentence)
        size += words
    if current:
        output.append(' '.join(current))
    return output


def clean_messages(msgs: list[dict]) -> list[dict]:
    """Allow system/user/assistant only; strip content, drop empty; at most
    one nonempty system, moved to front. Merge adjacent equal-role turns with
    newline after moving system. Content must be str; no input mutation.
    """
    system, turns = ([], [])
    for m in msgs:
        if m.get('role') not in {'system', 'user', 'assistant'} or not isinstance(m.get('content'), str):
            raise ValueError('Invalid message')
        text = m['content'].strip()
        if text:
            (system if m['role'] == 'system' else turns).append({'role': m['role'], 'content': text})
    if len(system) > 1:
        raise ValueError('Multiple system messages')
    output = system[:]
    for m in turns:
        if output and output[-1]['role'] == m['role']:
            output[-1]['content'] += '\n' + m['content']
        else:
            output.append(dict(m))
    return output
