"""One GTM harness; skill instructions and tools are resolved independently."""
import json
import re
import time
from agent_logic import run_sales_agent, MODEL_ID


def run_gtm(payload, model, loader, mcp):
    allowed_keys = {'skill_id', 'input', 'opportunity_id', 'request_id', 'actor', 'source', 'channel_id', 'authorization', 'identity'}
    if not isinstance(payload, dict) or not set(payload).issubset(allowed_keys):
        raise ValueError('Unknown GTM envelope fields')
    for name in ('opportunity_id', 'request_id'):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', payload.get(name, '')):
            raise ValueError('Invalid synthetic identifier')
    if not payload['opportunity_id'].startswith('demo-'):
        raise ValueError('Only demo opportunities are allowed')
    if type(payload.get('input')) is not str or len(payload['input']) > 10000:
        raise ValueError('Invalid skill input')
    start = time.monotonic()
    skill_id = payload.get('skill_id')
    skill = loader(skill_id)
    def tool(name, args):
        if name not in skill['allowed_tools']:
            raise ValueError('Tool not allowed by selected skill')
        began = time.monotonic()
        args = {**args, 'authorization': payload['authorization']} if 'authorization' in payload else args
        result = mcp(name, args)
        if 'error' in result:
            raise ValueError('Scoped tool denied or failed: ' + result['error'])
        tool_trace.append({'tool': name, 'latency_ms': round((time.monotonic() - began) * 1000)})
        return result
    tool_trace = []
    if skill_id == 'call-review':
        if not {'crm-tools___filter_findings', 'crm-tools___commit_sales'}.issubset(skill['allowed_tools']):
            raise ValueError('Call review has no approved write capability')
        def api(path, body):
            if path == '/exercises/P01':
                return tool('crm-tools___filter_findings', body['arguments'])
            if path == '/sales':
                return tool('crm-tools___commit_sales', body)
            raise ValueError('Skill has no route for this API')
        result = run_sales_agent({'transcript': payload['input'], 'opportunity_id': payload['opportunity_id'],
                                  'request_id': payload['request_id']}, model, api, skill['instructions'])
    elif skill_id == 'meeting-prep':
        context = tool('crm-tools___get_opportunity', {'opportunity_id': payload['opportunity_id']})
        if 'error' in context:
            raise ValueError('Opportunity context unavailable')
        response = model.converse(modelId=MODEL_ID, system=[{'text': skill['instructions']}],
            messages=[{'role': 'user', 'content': [{'text': json.dumps({'synthetic_context': context, 'request': payload['input']})}]}],
            inferenceConfig={'maxTokens': 500, 'temperature': 0})
        result = {'status': 'completed', 'answer': ' '.join(x['text'] for x in response['output']['message']['content'] if 'text' in x),
                  'context': context, 'model_id': MODEL_ID, 'model_calls': 1, 'usage': response.get('usage', {}), 'data_mode': 'synthetic'}
    else:
        raise ValueError('Unknown GTM skill')
    return {**result, 'skill_id': skill_id, 'skill_version': skill['version'], 'catalog_release': skill['release'],
            'request_id': payload['request_id'], 'actor': payload.get('actor'), 'credential_mode': 'service_role',
            'identity': payload.get('identity'),
            'tool_trace': tool_trace, 'latency_ms': round((time.monotonic() - start) * 1000)}
