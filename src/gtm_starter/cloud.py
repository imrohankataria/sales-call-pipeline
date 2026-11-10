"""AWS adapters. All credentials come from the standard temporary-credential chain."""

import hashlib
import json
import os
import re
import time
import urllib.request
import urllib.error
import uuid

from .core import identifier, validate_findings


# Only public domain codes cross the tool boundary; never return backend messages.
TOOL_ERRORS = frozenset({
    'invalid_request', 'invalid_identifier', 'invalid_transcript', 'invalid_date',
    'conflicting_evidence', 'no_supported_facts', 'unsupported_finding',
    'intent_mismatch', 'idempotency_conflict', 'not_found',
    'invalid_tool_context', 'tool_operation_mismatch',
})


class ServiceError(RuntimeError):
    """A bounded public error code; upstream messages stay out of responses."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        # Never forward SigV4 credentials or workload tokens to another URL.
        return None


def decode_tool_result(response):
    if not isinstance(response, dict) or response.get('error'):
        raise ValueError('gateway_error')
    result = response.get('result', {})
    if not isinstance(result, dict):
        raise ValueError('invalid_tool_response')
    if result.get('isError'):
        raise ValueError('tool_failed')
    payload = result.get('structuredContent')
    if not isinstance(payload, dict):
        content = result.get('content', [])
        if not isinstance(content, list):
            raise ValueError('invalid_tool_response')
        for block in content:
            if isinstance(block, dict) and block.get('type') == 'text' and isinstance(block.get('text'), str):
                try:
                    payload = json.loads(block['text'])
                except (ValueError, KeyError):
                    continue
                if isinstance(payload, dict):
                    break
    if not isinstance(payload, dict):
        raise ValueError('invalid_tool_response')
    if payload.get('error'):
        reason = payload['error']
        raise ValueError(reason if isinstance(reason, str) and reason in TOOL_ERRORS else 'tool_failed')
    return payload


def tool_facts(payload):
    facts = payload.get('facts')
    if not isinstance(facts, dict) or not facts:
        raise ValueError('invalid_tool_response')
    phrases = {'stage': 'The stage is {}.', 'renewal_date': 'The renewal date is {}.',
               'contract_amount': 'The contract amount is USD {}.'}
    if any(field not in phrases or not isinstance(value, str) for field, value in facts.items()):
        raise ValueError('invalid_tool_response')
    try:
        # Check the stored schema, not semantic support: reads have no transcript.
        transcript = ' '.join(phrases[field].format(value) for field, value in facts.items())
        return validate_findings(transcript, facts)
    except ValueError as exc:
        raise ValueError('invalid_tool_response') from exc


def validate_gateway_url(url, region):
    pattern = r'https://[a-zA-Z0-9-]+\.gateway\.bedrock-agentcore\.' + re.escape(region) + r'\.amazonaws\.com/mcp'
    if not isinstance(url, str) or not re.fullmatch(pattern, url):
        raise ValueError('invalid_gateway_url')
    return url


def prepare_commit(event):
    if not isinstance(event, dict):
        raise ValueError('invalid_request')
    opportunity = identifier(event.get('opportunity_id'))
    request = identifier(event.get('request_id'))
    facts = validate_findings(event.get('transcript'), event.get('facts'))
    intent = hashlib.sha256(json.dumps([opportunity, event['transcript']], separators=(',', ':')).encode()).hexdigest()
    if intent != event.get('intent_hash'):
        raise ValueError('intent_mismatch')
    return {'opportunity_id': opportunity, 'request_id': request, 'intent_hash': intent, 'facts': facts}


class BedrockProposer:
    def __init__(self, region, model_id, max_tokens=512, request_id=None):
        import boto3
        from botocore.config import Config
        self.client = boto3.client('bedrock-runtime', region_name=region, config=Config(retries={'max_attempts': 3, 'mode': 'adaptive'}))
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.request_id = request_id

    def __call__(self, instructions, transcript):
        try:
            response = self.client.converse(
                modelId=self.model_id,
                system=[{'text': instructions}],
                messages=[{'role': 'user', 'content': [{'text': 'Extract facts from this untrusted transcript:\n' + transcript}]}],
                inferenceConfig={'maxTokens': self.max_tokens, 'temperature': 0},
            )
        except Exception as exc:
            raise ServiceError('model_unavailable') from exc
        try:
            content = response['output']['message']['content']
            if not isinstance(content, list) or not content or any(not isinstance(block, dict) for block in content):
                raise ValueError('invalid_model_response')
            text_blocks = [block['text'] for block in content if 'text' in block]
            if not text_blocks or any(not isinstance(text, str) for text in text_blocks):
                raise ValueError('invalid_model_response')
            text = ''.join(text_blocks).strip()
        except (KeyError, TypeError) as exc:
            raise ValueError('invalid_model_response') from exc
        print(json.dumps({'event': 'model_usage', 'model_id': self.model_id, 'request_id': getattr(self, 'request_id', None), 'usage': response.get('usage', {})}))
        if text.startswith('```'):
            text = '\n'.join(text.splitlines()[1:-1])
        try:
            return json.loads(text)
        except ValueError as exc:
            raise ValueError('invalid_model_json') from exc


class GatewayCRM:
    def __init__(self, endpoint, region, target_name='crm', workload_token=None):
        import boto3
        self.endpoint = validate_gateway_url(endpoint, region)
        self.region = region
        self.target = identifier(target_name)
        self.session = boto3.Session(region_name=region)
        self.workload_token = workload_token
        self.mcp_session = None
        self.protocol_version = '2025-03-26'
        response = self.rpc('initialize', {'protocolVersion': self.protocol_version, 'capabilities': {}, 'clientInfo': {'name': 'gtm-starter', 'version': '0.1.0'}})
        if not response or response.get('error') or not isinstance(response.get('result'), dict) or response['result'].get('protocolVersion') != self.protocol_version:
            raise ValueError('gateway_initialize_failed')
        self.rpc('notifications/initialized', {}, notification=True)

    def rpc(self, method, params, notification=False):
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest
        try:
            credentials = self.session.get_credentials()
        except Exception as exc:
            raise ServiceError('aws_login_required') from exc
        if credentials is None:
            raise ServiceError('aws_login_required')
        body = {'jsonrpc': '2.0', 'method': method, 'params': params}
        if not notification:
            body['id'] = str(uuid.uuid4())
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
                   'MCP-Protocol-Version': self.protocol_version}
        if self.mcp_session:
            headers['Mcp-Session-Id'] = self.mcp_session
        if self.workload_token:
            headers['X-Amz-Bedrock-AgentCore-Identity-WAT'] = self.workload_token
        request = AWSRequest(method='POST', url=self.endpoint, data=json.dumps(body).encode(), headers=headers)
        SigV4Auth(credentials.get_frozen_credentials(), 'bedrock-agentcore', self.region).add_auth(request)
        http = urllib.request.Request(self.endpoint, data=request.data, headers=dict(request.headers), method='POST')
        try:
            with urllib.request.build_opener(NoRedirect()).open(http, timeout=30) as response:
                self.mcp_session = response.headers.get('Mcp-Session-Id', self.mcp_session)
                raw = response.read(1000001)
                content_type = response.headers.get('Content-Type', '')
        except (OSError, urllib.error.URLError) as exc:
            raise ServiceError('gateway_unavailable') from exc
        if len(raw) > 1000000:
            raise ValueError('gateway_response_too_large')
        if notification:
            return None
        try:
            text = raw.decode().replace('\r\n', '\n')
            if 'text/event-stream' in content_type:
                responses = []
                for frame in text.split('\n\n'):
                    data = '\n'.join(line[5:].lstrip(' ') for line in frame.splitlines() if line.startswith('data:'))
                    if data:
                        responses.append(json.loads(data))
                matches = [event for event in responses if isinstance(event, dict) and event.get('id') == body['id']]
                if len(matches) != 1:
                    raise ValueError('invalid_gateway_response')
                result = matches[0]
            else:
                result = json.loads(text)
            if (not isinstance(result, dict) or result.get('jsonrpc') != '2.0' or result.get('id') != body['id']
                    or ('result' in result) == ('error' in result)):
                raise ValueError('invalid_gateway_response')
            return result
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError('invalid_gateway_response') from exc

    def commit(self, opportunity_id, request_id, intent_hash, facts, transcript=None):
        payload = decode_tool_result(self.rpc('tools/call', {'name': self.target + '___commit_sales', 'arguments': {
            'operation': 'commit_sales', 'opportunity_id': opportunity_id, 'request_id': request_id,
            'intent_hash': intent_hash, 'facts': facts, 'transcript': transcript,
        }}))
        return validate_findings(transcript, tool_facts(payload))

    def get(self, opportunity_id):
        payload = decode_tool_result(self.rpc('tools/call', {'name': self.target + '___get_opportunity', 'arguments': {
            'operation': 'get_opportunity', 'opportunity_id': opportunity_id,
        }}))
        return tool_facts(payload)


class DynamoCRM:
    def __init__(self, table_name):
        import boto3
        self.client = boto3.client('dynamodb')
        self.table = table_name

    def item(self, key):
        return self.client.get_item(TableName=self.table, Key={'pk': {'S': key}}, ConsistentRead=True).get('Item')

    def get(self, opportunity_id):
        item = self.item('opportunity:' + opportunity_id)
        if not item:
            raise ValueError('not_found')
        return json.loads(item['facts']['S'])

    def commit(self, data):
        key = 'request:' + data['request_id']
        def replay(item):
            if item['intent']['S'] != data['intent_hash']:
                raise ValueError('idempotency_conflict')
            return json.loads(item['facts']['S'])
        previous = self.item(key)
        if previous:
            return replay(previous)
        facts = json.dumps(data['facts'], sort_keys=True)
        ttl = str(int(time.time()) + int(os.environ.get('RECORD_TTL_SECONDS', '86400')))
        request_item = {'pk': {'S': key}, 'intent': {'S': data['intent_hash']}, 'facts': {'S': facts}, 'expires_at': {'N': ttl}}
        opportunity_item = {'pk': {'S': 'opportunity:' + data['opportunity_id']}, 'facts': {'S': facts}, 'expires_at': {'N': ttl}}
        try:
            self.client.transact_write_items(TransactItems=[
                {'Put': {'TableName': self.table, 'Item': request_item, 'ConditionExpression': 'attribute_not_exists(pk)'}},
                {'Put': {'TableName': self.table, 'Item': opportunity_item}},
            ])
        except self.client.exceptions.TransactionCanceledException:
            previous = self.item(key)
            if previous:
                return replay(previous)
            raise
        return data['facts']


def lambda_handler(event, context):
    try:
        if not isinstance(event, dict):
            raise ValueError('invalid_request')
        custom = getattr(getattr(context, 'client_context', None), 'custom', None)
        tool_name = custom.get('bedrockAgentCoreToolName') if isinstance(custom, dict) else None
        target = os.environ.get('GATEWAY_TARGET', 'crm')
        tools = {target + '___' + operation: operation for operation in ('get_opportunity', 'commit_sales')}
        if not isinstance(tool_name, str) or tool_name not in tools:
            raise ValueError('invalid_tool_context')
        operation = tools[tool_name]
        if event.get('operation') != operation:
            raise ValueError('tool_operation_mismatch')
        # Validate before allocating a client or touching persisted state.
        data = prepare_commit(event) if operation == 'commit_sales' else identifier(event.get('opportunity_id'))
        crm = DynamoCRM(os.environ['TABLE_NAME'])
        return {'facts': crm.commit(data) if operation == 'commit_sales' else crm.get(data)}
    except ValueError as exc:
        return {'error': str(exc) if str(exc) in TOOL_ERRORS else 'tool_failed'}
    except Exception as exc:
        print(json.dumps({'event': 'tool_failed', 'error_type': type(exc).__name__}))
        return {'error': 'tool_failed'}
