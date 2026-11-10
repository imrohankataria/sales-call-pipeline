"""Minimal authenticated JSON-RPC client for the AgentCore MCP Gateway."""
import json
import urllib.request
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from skill_catalog import KNOWN_TOOLS


def decode_response(raw):
    text = raw.decode()
    if text.lstrip().startswith('{'):
        return json.loads(text)
    for line in text.splitlines():
        if line.startswith('data: '):
            result = json.loads(line[6:])
            if 'result' in result or 'error' in result:
                return result
    raise ValueError('Gateway returned no MCP result')


def rpc(session, url, method, params=None):
    data = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}}).encode()
    request = AWSRequest(method='POST', url=url, data=data,
        headers={'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream', 'MCP-Protocol-Version': '2025-03-26'})
    from bedrock_agentcore.runtime import BedrockAgentCoreContext
    wat = BedrockAgentCoreContext.get_workload_access_token()
    if wat:
        request.headers['X-Amz-Bedrock-AgentCore-Identity-WAT'] = wat
    SigV4Auth(session.get_credentials().get_frozen_credentials(), 'bedrock-agentcore', session.region_name).add_auth(request)
    req = urllib.request.Request(url, data=data, headers=dict(request.prepare().headers), method='POST')
    with urllib.request.urlopen(req, timeout=25) as response:
        result = decode_response(response.read())
    if 'error' in result:
        raise ValueError('MCP request failed: ' + str(result['error'].get('code')))
    return result['result']


def call_tool(session, url, name, arguments):
    if name not in KNOWN_TOOLS:
        raise ValueError('Unknown Gateway tool')
    result = rpc(session, url, 'tools/call', {'name': name, 'arguments': arguments})
    if result.get('isError'):
        raise ValueError('Gateway tool execution failed')
    if 'structuredContent' in result:
        return result['structuredContent']
    for part in result.get('content', []):
        if part.get('type') == 'text':
            return json.loads(part['text'])
    raise ValueError('Gateway returned no tool content')
