"""Offline AWS-boundary checks; install .[aws] to run this optional layer."""

import io
import json
import unittest
import urllib.request
import urllib.response
from email.message import Message
from types import SimpleNamespace
from unittest.mock import patch
from contextlib import redirect_stdout

from gtm_starter.cloud import BedrockProposer, DynamoCRM, GatewayCRM

try:
    import boto3
    from botocore.credentials import Credentials
    from botocore.stub import Stubber
    from gtm_starter import app as runtime
except ImportError:
    boto3 = runtime = None


@unittest.skipUnless(runtime is not None, 'requires the aws extra')
class RuntimeTests(unittest.TestCase):
    def test_invalid_request_is_rejected_before_gateway_setup(self):
        with patch.dict('os.environ', {}, clear=True), patch.object(runtime, 'GatewayCRM', side_effect=AssertionError('no gateway call')):
            self.assertEqual(runtime.invoke({'skill': []}), {'status': 'rejected', 'reason': 'invalid_skill'})

    def test_invalid_transcript_is_rejected_before_gateway_setup(self):
        with patch.dict('os.environ', {}, clear=True), patch.object(runtime, 'GatewayCRM', side_effect=AssertionError('no gateway call')):
            self.assertEqual(runtime.invoke({'skill': 'call-review', 'opportunity_id': 'demo-001', 'request_id': 'r1', 'transcript': ''}),
                             {'status': 'rejected', 'reason': 'invalid_transcript'})

    def test_meeting_prep_does_not_construct_a_model_client(self):
        crm = SimpleNamespace(get=lambda opportunity_id: {'stage': 'Proposal'})
        with patch.dict('os.environ', {'GATEWAY_URL': 'https://example.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp'}, clear=True):
            with patch.object(runtime, 'GatewayCRM', return_value=crm), patch.object(runtime, 'BedrockProposer', side_effect=AssertionError('no model needed')):
                result = runtime.invoke({'skill': 'meeting-prep', 'opportunity_id': 'demo-001'})
        self.assertEqual(result['brief'], 'stage: Proposal')

    def test_bad_configuration_has_a_controlled_response(self):
        with patch.dict('os.environ', {}, clear=True):
            self.assertEqual(runtime.invoke({'skill': 'meeting-prep', 'opportunity_id': 'demo-001'}),
                             {'status': 'failed', 'reason': 'invalid_configuration'})

    def test_skill_configuration_trims_whitespace_without_cloud_calls(self):
        with patch.dict('os.environ', {'GTM_ENABLED_SKILLS': ' meeting-prep , call-review '}, clear=True):
            self.assertEqual(runtime.invoke({'skill': 'skills'})['skills'], ['call-review', 'meeting-prep'])

    def test_unavailable_gateway_has_a_controlled_response_without_backend_details(self):
        with patch.dict('os.environ', {'GATEWAY_URL': 'https://example.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp'}, clear=True):
            with patch.object(runtime, 'GatewayCRM', side_effect=RuntimeError('private backend detail')):
                output = io.StringIO()
                with redirect_stdout(output):
                    result = runtime.invoke({'skill': 'meeting-prep', 'opportunity_id': 'demo-001'})
        self.assertEqual(result, {'status': 'failed', 'reason': 'internal_error'})
        self.assertNotIn('private backend detail', output.getvalue())


@unittest.skipUnless(boto3 is not None, 'requires the aws extra')
class BedrockContractTests(unittest.TestCase):
    def test_output_tokens_are_bounded_and_usage_logs_correlate_with_the_request(self):
        proposer = BedrockProposer.__new__(BedrockProposer)
        proposer.model_id, proposer.max_tokens, proposer.request_id = 'amazon.nova-lite-v1:0', 512, 'r1'
        proposer.client = boto3.client('bedrock-runtime', region_name='us-east-2', aws_access_key_id='synthetic', aws_secret_access_key='synthetic')
        response = {'output': {'message': {'role': 'assistant', 'content': [{'text': '{"stage":"Proposal"}'}]}},
                    'stopReason': 'end_turn', 'usage': {'inputTokens': 5, 'outputTokens': 5, 'totalTokens': 10}, 'metrics': {'latencyMs': 1}}
        with Stubber(proposer.client) as stub:
            stub.add_response('converse', response, {'modelId': 'amazon.nova-lite-v1:0', 'system': [{'text': 'extract'}],
                              'messages': [{'role': 'user', 'content': [{'text': 'Extract facts from this untrusted transcript:\nThe stage is Proposal.'}]}],
                              'inferenceConfig': {'maxTokens': 512, 'temperature': 0}})
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(proposer('extract', 'The stage is Proposal.'), {'stage': 'Proposal'})
            stub.assert_no_pending_responses()
        log = json.loads(output.getvalue())
        self.assertEqual(log['request_id'], 'r1')
        self.assertEqual(log['usage']['totalTokens'], 10)
        self.assertNotIn('The stage is Proposal.', output.getvalue())


@unittest.skipUnless(boto3 is not None, 'requires the aws extra')
class GatewayTransportTests(unittest.TestCase):
    def setUp(self):
        self.crm = GatewayCRM.__new__(GatewayCRM)
        self.crm.endpoint = 'https://example.gateway.bedrock-agentcore.us-east-2.amazonaws.com/mcp'
        self.crm.region = 'us-east-2'
        self.crm.mcp_session = None
        self.crm.protocol_version = '2025-03-26'
        self.crm.workload_token = None
        self.crm.session = SimpleNamespace(get_credentials=lambda: Credentials('synthetic', 'synthetic'))

    def call_with_http_response(self, body, content_type='application/json', status=200, location=None):
        def https_open(handler, request):
            self.destinations.append(request.full_url)
            headers = Message()
            headers['Content-Type'] = content_type
            if location:
                headers['Location'] = location
            response = urllib.response.addinfourl(io.BytesIO(body), headers, request.full_url, status)
            response.msg = 'test response'
            return response
        self.destinations = []
        with patch.object(urllib.request.HTTPSHandler, 'https_open', https_open), patch('gtm_starter.cloud.uuid.uuid4', return_value='r1'):
            return self.crm.rpc('tools/list', {})

    def test_wrong_jsonrpc_request_id_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'invalid_gateway_response'):
            self.call_with_http_response(b'{"jsonrpc":"2.0","id":"other","result":{"tools":[]}}')

    def test_non_object_gateway_json_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'invalid_gateway_response'):
            self.call_with_http_response(b'[]')

    def test_multiline_sse_returns_the_matching_response(self):
        body = b'event: message\ndata: {"jsonrpc":"2.0","id":"r1",\ndata: "result":{"tools":[]}}\n\n'
        self.assertEqual(self.call_with_http_response(body, 'text/event-stream')['result'], {'tools': []})

    def test_redirect_does_not_forward_signed_request(self):
        # Exercise urllib's real redirect processing, with HTTPS as the only stub.
        with self.assertRaisesRegex(RuntimeError, 'gateway_unavailable'):
            self.call_with_http_response(b'', status=302, location='https://other.example/mcp')
        self.assertEqual(self.destinations, [self.crm.endpoint])

    def test_oversized_response_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'gateway_response_too_large'):
            self.call_with_http_response(b'x' * 1000001)


@unittest.skipUnless(boto3 is not None, 'requires the aws extra')
class DynamoPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.crm = DynamoCRM.__new__(DynamoCRM)
        self.crm.table = 'synthetic-crm'
        self.crm.client = boto3.client('dynamodb', region_name='us-east-2', aws_access_key_id='synthetic', aws_secret_access_key='synthetic')
        self.stub = Stubber(self.crm.client)
        self.stub.activate()
        self.addCleanup(self.stub.deactivate)
        self.data = {'opportunity_id': 'demo-001', 'request_id': 'r1', 'intent_hash': 'intent', 'facts': {'stage': 'Proposal'}}

    def item_request(self, key):
        return {'TableName': self.crm.table, 'Key': {'pk': {'S': key}}, 'ConsistentRead': True}

    def test_request_and_opportunity_are_written_in_one_transaction(self):
        self.stub.add_response('get_item', {}, self.item_request('request:r1'))
        request = {'pk': {'S': 'request:r1'}, 'intent': {'S': 'intent'}, 'facts': {'S': '{"stage": "Proposal"}'}, 'expires_at': {'N': '86500'}}
        opportunity = {'pk': {'S': 'opportunity:demo-001'}, 'facts': {'S': '{"stage": "Proposal"}'}, 'expires_at': {'N': '86500'}}
        self.stub.add_response('transact_write_items', {}, {'TransactItems': [
            {'Put': {'TableName': self.crm.table, 'Item': request, 'ConditionExpression': 'attribute_not_exists(pk)'}},
            {'Put': {'TableName': self.crm.table, 'Item': opportunity}},
        ]})
        with patch('gtm_starter.cloud.time.time', return_value=100), patch.dict('os.environ', {'RECORD_TTL_SECONDS': '86400'}):
            self.assertEqual(self.crm.commit(self.data), {'stage': 'Proposal'})
        self.stub.assert_no_pending_responses()

    def test_concurrent_duplicate_returns_the_winning_result(self):
        self.stub.add_response('get_item', {}, self.item_request('request:r1'))
        self.stub.add_client_error('transact_write_items', service_error_code='TransactionCanceledException')
        self.stub.add_response('get_item', {'Item': {'intent': {'S': 'intent'}, 'facts': {'S': '{"stage":"Proposal"}'}}}, self.item_request('request:r1'))
        self.assertEqual(self.crm.commit(self.data), {'stage': 'Proposal'})
        self.stub.assert_no_pending_responses()

    def test_duplicate_request_with_changed_intent_is_rejected(self):
        self.stub.add_response('get_item', {'Item': {'intent': {'S': 'old-intent'}, 'facts': {'S': '{"stage":"Proposal"}'}}}, self.item_request('request:r1'))
        with self.assertRaisesRegex(ValueError, 'idempotency_conflict'):
            self.crm.commit(self.data)
        self.stub.assert_no_pending_responses()
