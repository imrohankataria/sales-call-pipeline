"""Small, deterministic GTM workflow; model output is always untrusted."""

import hashlib
import json
import re
import sqlite3
from contextlib import closing
from datetime import date
from importlib.resources import files
from pathlib import Path


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value):
        raise ValueError('invalid_identifier')
    return value


def source_facts(transcript):
    if not isinstance(transcript, str) or not 1 <= len(transcript) <= 10000:
        raise ValueError('invalid_transcript')
    patterns = {
        'stage': r'\bThe stage is (Prospecting|Qualification|Proposal|Negotiation|Closed Won|Closed Lost)\.',
        'renewal_date': r'\bThe renewal date is (\d{4}-\d{2}-\d{2})\.',
        'contract_amount': r'\bThe contract amount is USD ([0-9]{1,10}(?:\.[0-9]{1,2})?)\.(?![0-9])',
    }
    result = {}
    for field, pattern in patterns.items():
        values = set(re.findall(pattern, transcript))
        if len(values) > 1:
            raise ValueError('conflicting_evidence')
        if values:
            result[field] = values.pop()
    if 'renewal_date' in result:
        try:
            date.fromisoformat(result['renewal_date'])
        except ValueError as exc:
            raise ValueError('invalid_date') from exc
    return result


def validate_findings(transcript, findings):
    supported = source_facts(transcript)
    if not isinstance(findings, dict) or not findings:
        raise ValueError('no_supported_facts')
    for field, value in findings.items():
        if field not in supported or not isinstance(value, str) or value != supported[field]:
            raise ValueError('unsupported_finding')
    return dict(findings)


class Catalog:
    def __init__(self, entries):
        self.entries = entries

    @classmethod
    def default(cls):
        return cls(json.loads(files('gtm_starter').joinpath('catalog.json').read_text()))

    def get(self, name):
        if name not in self.entries:
            raise ValueError('unknown_skill')
        entry = self.entries[name]
        path = entry['path']
        if '..' in Path(path).parts or Path(path).is_absolute():
            raise ValueError('invalid_skill_path')
        instructions = files('gtm_starter').joinpath(path).read_text()
        return {**entry, 'instructions': instructions}


class LocalCRM:
    """SQLite transactions keep the request ledger and current facts consistent."""

    def __init__(self, path):
        self.path = Path(path)

    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path)
        db.execute('CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, intent TEXT, facts TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS opportunities (id TEXT PRIMARY KEY, facts TEXT)')
        return db

    def commit(self, opportunity_id, request_id, intent_hash, facts, transcript=None):
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT intent, facts FROM requests WHERE id=?', (request_id,)).fetchone()
            if previous:
                if previous[0] != intent_hash:
                    raise ValueError('idempotency_conflict')
                return json.loads(previous[1])
            data = json.dumps(facts, sort_keys=True)
            db.execute('INSERT INTO requests VALUES (?, ?, ?)', (request_id, intent_hash, data))
            db.execute('INSERT INTO opportunities VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET facts=excluded.facts', (opportunity_id, data))
        return dict(facts)

    def get(self, opportunity_id):
        if not self.path.exists():
            raise ValueError('not_found')
        with closing(self.connect()) as db, db:
            row = db.execute('SELECT facts FROM opportunities WHERE id=?', (opportunity_id,)).fetchone()
        if not row:
            raise ValueError('not_found')
        return json.loads(row[0])


class Workflow:
    def __init__(self, catalog, crm, proposer=None, enabled_skills=None):
        self.catalog = catalog
        self.crm = crm
        self.proposer = proposer
        self.enabled = set(enabled_skills if enabled_skills is not None else catalog.entries)

    def validate_request(self, request):
        """Reject invalid requests before any cloud dependency is constructed."""
        if not isinstance(request, dict):
            raise ValueError('invalid_request')
        skill = request.get('skill')
        if not isinstance(skill, str) or not skill:
            raise ValueError('invalid_skill')
        if skill == 'skills':
            return skill, None, None
        if skill not in self.enabled:
            raise ValueError('skill_not_enabled')
        entry = self.catalog.get(skill)
        opportunity_id = identifier(request.get('opportunity_id'))
        if skill == 'meeting-prep':
            if 'get_opportunity' not in entry['tools']:
                raise ValueError('tool_not_enabled')
        elif skill == 'call-review' and 'commit_sales' in entry['tools']:
            identifier(request.get('request_id'))
            if not source_facts(request.get('transcript')):
                raise ValueError('no_supported_facts')
        else:
            raise ValueError('unknown_skill')
        return skill, entry, opportunity_id

    def run(self, request):
        skill, entry, opportunity_id = self.validate_request(request)
        if skill == 'skills':
            return {'skills': sorted(self.enabled & self.catalog.entries.keys())}
        if skill == 'meeting-prep':
            facts = self.crm.get(opportunity_id)
            brief = '\n'.join(f'{key}: {value}' for key, value in sorted(facts.items()))
            return {'skill': skill, 'version': entry['version'], 'opportunity_id': opportunity_id, 'facts': facts, 'brief': brief}
        request_id = identifier(request.get('request_id'))
        transcript = request.get('transcript')
        supported = source_facts(transcript)
        if not supported:
            raise ValueError('no_supported_facts')
        proposed = self.proposer(entry['instructions'], transcript) if self.proposer else supported
        facts = validate_findings(transcript, proposed)
        intent = hashlib.sha256(json.dumps([opportunity_id, transcript], separators=(',', ':')).encode()).hexdigest()
        committed = self.crm.commit(opportunity_id, request_id, intent, facts, transcript=transcript)
        return {'skill': skill, 'version': entry['version'], 'opportunity_id': opportunity_id, 'request_id': request_id, 'facts': committed}
