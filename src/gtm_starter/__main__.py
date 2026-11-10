"""Local demo has no model call, network request, or AWS login requirement."""

import argparse
import json
from pathlib import Path

from .core import Catalog, LocalCRM, Workflow

parser = argparse.ArgumentParser()
parser.add_argument('--db', default='.local/crm.sqlite3')
parser.add_argument('--payload', type=Path)
args = parser.parse_args()
workflow = Workflow(Catalog.default(), LocalCRM(args.db))
if args.payload:
    requests = [json.loads(args.payload.read_text())]
else:
    requests = [
        {'skill': 'skills'},
        {'skill': 'call-review', 'opportunity_id': 'demo-001', 'request_id': 'demo-review-001', 'transcript': 'The stage is Proposal. The renewal date is 2027-02-01. The contract amount is USD 24000.'},
        {'skill': 'meeting-prep', 'opportunity_id': 'demo-001'},
    ]
for request in requests:
    print(json.dumps(workflow.run(request), indent=2))
