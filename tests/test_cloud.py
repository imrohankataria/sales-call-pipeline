import hashlib
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from gtm_starter.cloud import BedrockProposer, GatewayCRM, decode_tool_result, lambda_handler, prepare_commit, validate_gateway_url


class CloudBoundaryTests(unittest.TestCase):
    def test_gateway_result_decodes_structured_and_text_outputs(self):
        self.assertEqual(decode_tool_result({'result': {'structuredContent': {'facts': {'stage': 'Proposal'}}}}), {'facts': {'stage': 'Proposal'}})
        self.assertEqual(decode_tool_result({'result': {'content': [{'type': 'text', 'text': '{"facts": {"stage": "Proposal"}}'}]}}), {'facts': {'stage': 'Proposal'}})

    def test_gateway_errors_are_not_treated_as_success(self):
        for response in [{'error': {'code': -1}}, {'result': {'isError': True}}, {'result': {'content': []}}]:
            with self.subTest(response=response), self.assertRaises(ValueError):
                decode_tool_result(response)

    def test_malformed_gateway_shapes_fail_with_a_controlled_error(self):
        for response in [{'result': None}, {'result': []}, {'result': {'content': None}}, {'result': {'content': [None]}}, {'result': {'content': [{'type': 'text', 'text': None}]}}]:
            with self.subTest(response=response), self.assertRaisesRegex(ValueError, 'invalid_tool_response'):
                decode_tool_result(response)

    def test_credentials_are_signed_only_for_an_aws_gateway_endpoint(self):
        self.assertEqual(validate_gateway_url('https://example.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp', 'us-east-2'), 'https://example.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp')
        for url in ['http://example.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp', 'https://evil.example/mcp', 'https://example.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_gateway_url(url, 'us-east-2')

    def test_tool_independently_rejects_tampered_values_and_intent(self):
        transcript = 'The stage is Proposal.'
        intent = hashlib.sha256(json.dumps(['demo-001', transcript], separators=(',', ':')).encode()).hexdigest()
        event = {'opportunity_id': 'demo-001', 'request_id': 'r1', 'transcript': transcript, 'intent_hash': intent, 'facts': {'stage': 'Proposal'}}
        self.assertEqual(prepare_commit(event)['facts'], {'stage': 'Proposal'})
        with self.assertRaisesRegex(ValueError, 'unsupported_finding'):
            prepare_commit({**event, 'facts': {'stage': 'Closed Won'}})
        with self.assertRaisesRegex(ValueError, 'intent_mismatch'):
            prepare_commit({**event, 'intent_hash': 'wrong'})

    def test_prepare_commit_rejects_non_objects(self):
        for event in [None, [], 'write']:
            with self.subTest(event=event), self.assertRaisesRegex(ValueError, 'invalid_request'):
                prepare_commit(event)

    def test_read_tool_context_cannot_be_used_for_a_write(self):
        context = SimpleNamespace(client_context=SimpleNamespace(custom={'bedrockAgentCoreToolName': 'crm___get_opportunity'}))
        with patch('gtm_starter.cloud.DynamoCRM', side_effect=AssertionError('database must not be reached')):
            self.assertEqual(lambda_handler({'operation': 'commit_sales'}, context), {'error': 'tool_operation_mismatch'})

    def test_missing_gateway_tool_context_is_rejected(self):
        with patch('gtm_starter.cloud.DynamoCRM', side_effect=AssertionError('database must not be reached')):
            self.assertEqual(lambda_handler({'operation': 'get_opportunity'}, None), {'error': 'invalid_tool_context'})

    def test_configured_gateway_target_can_read_but_reports_missing_evidence(self):
        context = SimpleNamespace(client_context=SimpleNamespace(custom={'bedrockAgentCoreToolName': 'sales___get_opportunity'}))
        class MissingCRM:
            def __init__(self, table):
                pass
            def get(self, opportunity_id):
                raise ValueError('not_found')
        with patch.dict('os.environ', {'TABLE_NAME': 'synthetic', 'GATEWAY_TARGET': 'sales'}), patch('gtm_starter.cloud.DynamoCRM', MissingCRM):
            self.assertEqual(lambda_handler({'operation': 'get_opportunity', 'opportunity_id': 'demo-001'}, context), {'error': 'not_found'})

    def test_unrecognized_tool_error_does_not_expose_backend_details(self):
        with self.assertRaisesRegex(ValueError, '^tool_failed$'):
            decode_tool_result({'result': {'structuredContent': {'error': 'backend detail with a secret'}}})

    def test_missing_record_error_survives_the_gateway_boundary(self):
        with self.assertRaisesRegex(ValueError, '^not_found$'):
            decode_tool_result({'result': {'structuredContent': {'error': 'not_found'}}})

    def test_gateway_read_rejects_missing_or_malformed_facts(self):
        crm = GatewayCRM.__new__(GatewayCRM)
        crm.target = 'crm'
        for payload in [{}, {'facts': []}, {'facts': {'stage': 'Invented'}}, {'facts': {'renewal_date': '2027-02-30'}}]:
            with self.subTest(payload=payload), patch.object(crm, 'rpc', return_value={'result': {'structuredContent': payload}}):
                with self.assertRaisesRegex(ValueError, 'invalid_tool_response'):
                    crm.get('demo-001')

    def test_gateway_commit_cannot_return_an_unsupported_fact(self):
        crm = GatewayCRM.__new__(GatewayCRM)
        crm.target = 'crm'
        with patch.object(crm, 'rpc', return_value={'result': {'structuredContent': {'facts': {'stage': 'Closed Won'}}}}):
            with self.assertRaisesRegex(ValueError, 'unsupported_finding'):
                crm.commit('demo-001', 'r1', 'intent', {'stage': 'Proposal'}, transcript='The stage is Proposal.')

    def test_malformed_model_envelope_has_a_controlled_rejection(self):
        proposer = BedrockProposer.__new__(BedrockProposer)
        proposer.model_id, proposer.max_tokens = 'synthetic', 512
        for response in [{}, {'output': {'message': {'content': [None]}}}]:
            proposer.client = SimpleNamespace(converse=lambda **kwargs: response)
            with self.subTest(response=response), self.assertRaisesRegex(ValueError, 'invalid_model_response'):
                proposer('extract', 'The stage is Proposal.')

    def test_invalid_model_json_is_rejected(self):
        proposer = BedrockProposer.__new__(BedrockProposer)
        proposer.model_id, proposer.max_tokens = 'synthetic', 512
        proposer.client = SimpleNamespace(converse=lambda **kwargs: {'output': {'message': {'content': [{'text': 'not JSON'}]}}})
        with self.assertRaisesRegex(ValueError, 'invalid_model_json'):
            proposer('extract', 'The stage is Proposal.')


if __name__ == '__main__':
    unittest.main()
