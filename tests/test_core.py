import tempfile
import unittest
from pathlib import Path
import sqlite3
from unittest.mock import patch

from gtm_starter.core import Catalog, LocalCRM, Workflow, validate_findings


TRANSCRIPT = 'The stage is Proposal. The renewal date is 2027-02-01. The contract amount is USD 24000.'


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.crm = LocalCRM(Path(self.tmp.name) / 'crm.sqlite3')
        self.workflow = Workflow(Catalog.default(), self.crm)

    def test_review_then_prep_reads_persisted_supported_facts(self):
        result = self.workflow.run({'skill': 'call-review', 'opportunity_id': 'demo-001', 'request_id': 'r1', 'transcript': TRANSCRIPT})
        self.assertEqual(result['facts'], {'stage': 'Proposal', 'renewal_date': '2027-02-01', 'contract_amount': '24000'})
        reopened = Workflow(Catalog.default(), LocalCRM(Path(self.tmp.name) / 'crm.sqlite3'))
        prep = reopened.run({'skill': 'meeting-prep', 'opportunity_id': 'demo-001'})
        self.assertEqual(prep['facts'], result['facts'])
        self.assertIn('2027-02-01', prep['brief'])

    def test_replay_preserves_result_and_changed_intent_conflicts(self):
        request = {'skill': 'call-review', 'opportunity_id': 'demo-001', 'request_id': 'r1', 'transcript': TRANSCRIPT}
        first = self.workflow.run(request)
        self.assertEqual(first['facts'], self.workflow.run(request)['facts'])
        with self.assertRaisesRegex(ValueError, 'idempotency_conflict'):
            self.workflow.run({**request, 'transcript': TRANSCRIPT.replace('24000', '25000')})

    def test_missing_facts_never_creates_a_record(self):
        with self.assertRaisesRegex(ValueError, 'no_supported_facts'):
            self.workflow.run({'skill': 'call-review', 'opportunity_id': 'demo-001', 'request_id': 'r1', 'transcript': 'Hello there.'})
        with self.assertRaisesRegex(ValueError, 'not_found'):
            self.workflow.run({'skill': 'meeting-prep', 'opportunity_id': 'demo-001'})

    def test_conflicting_values_require_review(self):
        with self.assertRaisesRegex(ValueError, 'conflicting_evidence'):
            self.workflow.run({'skill': 'call-review', 'opportunity_id': 'demo-001', 'request_id': 'r1', 'transcript': TRANSCRIPT + ' The stage is Closed Won.'})

    def test_unknown_skills_and_bad_identifiers_are_rejected(self):
        for request in [{'skill': 'delete-everything'}, {'skill': 'meeting-prep', 'opportunity_id': '../../other'}]:
            with self.subTest(request=request), self.assertRaises(ValueError):
                self.workflow.run(request)

    def test_model_cannot_invent_or_change_a_supported_value(self):
        with self.assertRaisesRegex(ValueError, 'unsupported_finding'):
            validate_findings(TRANSCRIPT, {'stage': 'Closed Won'})
        with self.assertRaisesRegex(ValueError, 'unsupported_finding'):
            validate_findings(TRANSCRIPT, {'owner_email': 'someone@example.com'})
        self.assertEqual(validate_findings(TRANSCRIPT, {'contract_amount': '24000'}), {'contract_amount': '24000'})

    def test_zero_is_a_valid_amount_and_invalid_date_is_rejected(self):
        self.assertEqual(validate_findings('The contract amount is USD 0.', {'contract_amount': '0'}), {'contract_amount': '0'})
        with self.assertRaisesRegex(ValueError, 'invalid_date'):
            validate_findings('The renewal date is 2027-02-30.', {'renewal_date': '2027-02-30'})

    def test_skill_listing_does_not_touch_crm(self):
        self.assertEqual(self.workflow.run({'skill': 'skills'})['skills'], ['call-review', 'meeting-prep'])
        self.assertFalse((Path(self.tmp.name) / 'crm.sqlite3').exists())

    def test_malformed_skill_values_are_controlled_rejections(self):
        for skill in [None, [], {}, 42]:
            with self.subTest(skill=skill), self.assertRaisesRegex(ValueError, 'invalid_skill'):
                self.workflow.run({'skill': skill})

    def test_overprecise_amount_cannot_be_saved_as_an_integer(self):
        request = {'skill': 'call-review', 'opportunity_id': 'demo-001', 'request_id': 'r1',
                   'transcript': 'The contract amount is USD 1.234.'}
        with self.assertRaisesRegex(ValueError, 'no_supported_facts'):
            self.workflow.run(request)
        with self.assertRaisesRegex(ValueError, 'not_found'):
            self.crm.get('demo-001')

    def test_valid_decimal_and_zero_preserve_their_exact_values(self):
        for amount in ['0', '0.00', '24000.99']:
            with self.subTest(amount=amount):
                self.assertEqual(validate_findings(f'The contract amount is USD {amount}.',
                                                  {'contract_amount': amount}), {'contract_amount': amount})

    def test_replaying_old_request_does_not_overwrite_newer_snapshot(self):
        first = {'skill': 'call-review', 'opportunity_id': 'demo-001', 'request_id': 'r1', 'transcript': TRANSCRIPT}
        old = self.workflow.run(first)
        new = self.workflow.run({**first, 'request_id': 'r2', 'transcript': 'The stage is Closed Won.'})
        self.assertEqual(self.workflow.run(first)['facts'], old['facts'])
        self.assertEqual(self.crm.get('demo-001'), new['facts'])

    def test_disabled_skill_never_writes(self):
        read_only = Workflow(Catalog.default(), self.crm, enabled_skills=['meeting-prep'])
        with self.assertRaisesRegex(ValueError, 'skill_not_enabled'):
            read_only.run({'skill': 'call-review', 'opportunity_id': 'demo-001', 'request_id': 'r1', 'transcript': TRANSCRIPT})
        self.assertFalse(self.crm.path.exists())

    def test_database_connections_close_after_reads_and_writes(self):
        connections = []
        connect = sqlite3.connect
        def recording_connect(*args, **kwargs):
            db = connect(*args, **kwargs)
            connections.append(db)
            return db
        with patch('gtm_starter.core.sqlite3.connect', side_effect=recording_connect):
            self.workflow.run({'skill': 'call-review', 'opportunity_id': 'demo-001', 'request_id': 'r1', 'transcript': TRANSCRIPT})
            self.crm.get('demo-001')
        for db in connections:
            with self.assertRaisesRegex(sqlite3.ProgrammingError, 'closed database'):
                db.execute('SELECT 1')


if __name__ == '__main__':
    unittest.main()
