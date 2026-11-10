"""Gateway's deterministic tools. The model never owns write validation."""
import json
import os
import re
import time
import functools
from execution_identity import verify_grant, execution_secret
from exercise_api import commit_sales, run_exercise


def dispatch(name, args, table):
    if name == 'filter_findings':
        if set(args) != {'findings', 'threshold'} or args['threshold'] != 0.8:
            raise ValueError('This skill requires the fixed validation threshold')
        return {'result': run_exercise('P01', args)}
    if name not in ('commit_sales', 'get_opportunity'):
        return {'error': 'unknown_tool'}
    if not re.fullmatch(r'demo-[A-Za-z0-9_-]{1,80}', args.get('opportunity_id', '')):
        raise ValueError('Only synthetic demo opportunities are allowed')
    if name == 'commit_sales':
        return commit_sales(args, table)
    if set(args) != {'opportunity_id'}:
        raise ValueError('Supply opportunity_id only')
    from boto3.dynamodb.conditions import Key
    page = table.query(KeyConditionExpression=Key('opportunity_id').eq(args['opportunity_id']), ConsistentRead=True, Limit=100)
    items = sorted(page.get('Items', []), key=lambda x: int(x['created_at']))
    fields = {}
    for item in items:
        fields.update(json.loads(item['fields_json']))
    return {'opportunity_id': args['opportunity_id'], 'crm_fields': fields, 'event_count': len(items),
            'data_mode': 'synthetic', 'source': 'DynamoDB validated events', 'bounded_history': 100}


def handler(event, context):
    import boto3
    start = time.monotonic()
    custom = getattr(getattr(context, 'client_context', None), 'custom', {}) or {}
    full_name = custom.get('bedrockAgentCoreToolName', '')
    name = full_name.rsplit('___', 1)[-1]
    try:
        event = dict(event)
        authorization = event.pop('authorization', {})
        if not verify_grant(authorization, execution_secret(), name, event, int(time.time())):
            print(json.dumps({'event': 'gateway_tool_denied', 'tool': name, 'reason': 'invalid_or_expired_scope'}))
            return {'error': 'user_scope_denied'}
        grant = authorization['grant']
        result = dispatch(name, event, boto3.resource('dynamodb').Table(os.environ['CRM_TABLE']))
        print(json.dumps({'event': 'gateway_tool_completed', 'tool': name, 'request_id': grant['request_id'],
                          'user_id': grant['user_id'], 'skill_id': grant['skill_id'],
                          'write_status': result.get('write_status'), 'latency_ms': round((time.monotonic() - start) * 1000)}))
        return result
    except (ValueError, TypeError, KeyError) as error:
        return {'error': 'invalid_tool_input', 'message': str(error)}
