"""Slack ack/queue and retry-safe result delivery, using synthetic data only."""
import base64
import functools
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from slack_logic import verify_signature, parse_command

IMPLEMENTATION_HELP_URL = 'https://deploy.rohankataria.com'
ATTRIBUTION_FOOTER = ('\n\n_Built by Rohan Kataria · Want this in your organization? '
    '<' + IMPLEMENTATION_HELP_URL + '|Get in touch for implementation help>._')

def response(status, body):
    if body.get('response_type') and isinstance(body.get('text'), str):
        body = {**body, 'text': body['text'] + ATTRIBUTION_FOOTER}
    return {'statusCode': status, 'headers': {'content-type': 'application/json'}, 'body': json.dumps(body)}


def process_webhook(event, secret, enqueue, now):
    raw = (event.get('body') or '').encode()
    if event.get('isBase64Encoded'):
        raw = base64.b64decode(raw)
    if len(raw) > 20000:
        return response(413, {'error': 'payload_too_large'})
    headers = {k.lower(): v for k, v in event.get('headers', {}).items()}
    if not verify_signature(raw, headers, secret.get('signing_secret', ''), now):
        return response(401, {'error': 'invalid_slack_signature'})
    try:
        if headers.get('content-type', '').startswith('application/json'):
            body = json.loads(raw)
            if body.get('type') == 'url_verification':
                return response(200, {'challenge': body['challenge']})
            return response(200, {'ok': True, 'ignored': True})
        form = {k: v[0] for k, v in urllib.parse.parse_qs(raw.decode()).items()}
        print(json.dumps({'event': 'slack_actor_verified', 'team_id': form.get('team_id'),
                          'user_id': form.get('user_id'), 'user_name': form.get('user_name')}))
        payload = parse_command(form, secret.get('team_id'), secret.get('allowed_users', []), secret.get('skill_grants'))
        if payload.get('kind') == 'skill_directory':
            skills = '\n'.join('- ' + name + ' v1.0.0' for name in payload['permitted_skills']) or 'No skills granted.'
            return response(200, {'response_type': 'ephemeral', 'text':
                f"Verified Slack user: <@{payload['user_id']}>\nYour permitted skills:\n{skills}\n"
                'Use /gtm call-review demo-001 | transcript or /gtm meeting-prep demo-001.\n'
                'Execution uses a user-bound AgentCore workload identity and scoped service-role tools. No enterprise OAuth delegation is configured.'})
        enqueue(payload)
        return response(200, {'response_type': 'ephemeral', 'text': f"Queued {payload['skill_id']} for {payload['opportunity_id']}. Request: {payload['request_id']}"})
    except ValueError as error:
        return response(200, {'response_type': 'ephemeral', 'text': str(error)})


def credentials():
    import boto3
    return json.loads(boto3.client('secretsmanager').get_secret_value(SecretId=os.environ['SLACK_SECRET_ARN'])['SecretString'])


def enqueue(payload):
    import boto3
    boto3.client('sqs').send_message(QueueUrl=os.environ['QUEUE_URL'], MessageBody=json.dumps(payload))


def webhook(event, context):
    try:
        return process_webhook(event, credentials(), enqueue, int(time.time()))
    except Exception as error:
        print(json.dumps({'event': 'slack_ingress_error', 'error_type': type(error).__name__}))
        return response(503, {'error': 'ingress_unavailable'})


def backend(event, context):
    """IAM-authenticated backend uses the same harness; it is a service job."""
    try:
        payload = json.loads(event.get('body') or '{}')
        if set(payload) != {'skill_id', 'input', 'opportunity_id', 'request_id'}:
            raise ValueError('Supply skill_id, input, opportunity_id and request_id')
        from agent_logic import validate_payload
        validate_payload({'transcript': payload['input'] or 'Meeting preparation',
                          'opportunity_id': payload['opportunity_id'], 'request_id': payload['request_id']})
        if payload['skill_id'] not in ('call-review', 'meeting-prep') or not payload['opportunity_id'].startswith('demo-'):
            raise ValueError('Unsupported demo job')
        enqueue({**payload, 'source': 'backend', 'actor': {'credential_mode': 'service_role'}})
        return response(202, {'queued': True, 'request_id': payload['request_id']})
    except (ValueError, TypeError, KeyError) as error:
        return response(400, {'error': 'invalid_job', 'message': str(error)})


def execute_job(payload, stored, invoke, save, post):
    if stored.get('slack_ts') or stored.get('delivered_backend'):
        return stored
    result = stored.get('result') or invoke(payload)
    if result.get('status') not in ('completed',):
        raise RuntimeError('Agent did not complete: ' + result.get('status', 'unknown'))
    saved = {'result': result}
    save(saved)
    if payload.get('source') == 'slack':
        saved['slack_ts'] = post(payload, result)
    else:
        saved['delivered_backend'] = True
    save(saved)
    return saved


def slack_post(payload, result):
    secret = credentials()
    authoritative = result.get('sales_result') or result.get('context')
    text = (f"*GTM agent · {result.get('skill_id')} v{result.get('skill_version')}*\n"
            f"Request: `{payload['request_id']}` · Model: `{result.get('model_id')}`\n"
            f"Credential mode: service role; Slack actor: <@{payload['actor']['user_id']}>\n"
            f"User identity: `{result.get('identity', {}).get('user_id')}` · Runtime workload token present: `{result.get('workload_identity_token_present')}`\n"
            f"*Authoritative synthetic result*\n```{json.dumps(authoritative, indent=2)[:6000]}```\n"
            f"{result.get('answer', '')[:2000]}\nAgent latency: {result.get('latency_ms')} ms · {result.get('model_calls')} model calls")
    data = json.dumps({'channel': payload['channel_id'], 'text': text + ATTRIBUTION_FOOTER, 'unfurl_links': False, 'unfurl_media': False}).encode()
    req = urllib.request.Request('https://slack.com/api/chat.postMessage', data=data,
        headers={'Authorization': 'Bearer ' + secret['bot_token'], 'Content-Type': 'application/json; charset=utf-8'})
    with urllib.request.urlopen(req, timeout=15) as reply:
        body = json.load(reply)
    if not body.get('ok'):
        raise RuntimeError('Slack delivery failed: ' + body.get('error', 'unknown'))
    return body['ts']


def claim_job(table, payload, now):
    intent_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    table.update_item(Key={'request_id': payload['request_id']}, UpdateExpression='SET lease_until = :lease, #expiry = :ttl, intent_hash = :hash',
        ConditionExpression='(attribute_not_exists(lease_until) OR lease_until < :now) AND (attribute_not_exists(intent_hash) OR intent_hash = :hash)',
        ExpressionAttributeNames={'#expiry': 'ttl'},
        ExpressionAttributeValues={':lease': now + 130, ':ttl': now + 86400, ':hash': intent_hash, ':now': now})


def runtime_identity(body, secret):
    if body.get('source') != 'slack':
        return None, 'service_workload'
    actor = body.get('actor', {})
    if actor.get('team_id') != secret['team_id'] or actor.get('user_id') not in secret['allowed_users']:
        raise ValueError('Slack actor not authorized')
    if body['skill_id'] not in secret['skill_grants'].get(actor['user_id'], []):
        raise ValueError('Skill permission revoked')
    return 'slack:' + actor['team_id'] + ':' + actor['user_id'], 'runtime_user'


def worker(event, context):
    import boto3
    from botocore.config import Config
    table = boto3.resource('dynamodb').Table(os.environ['JOBS_TABLE'])
    runtime = boto3.client('bedrock-agentcore', config=Config(read_timeout=100, retries={'total_max_attempts': 1}))
    failures = []
    for record in event['Records']:
        payload = json.loads(record['body']); key = {'request_id': payload['request_id']}
        now = int(time.time())
        try:
            claim_job(table, payload, now)
            item = table.get_item(Key=key, ConsistentRead=True).get('Item', {})
            stored = json.loads(item.get('state_json', '{}'))
            def save(state):
                table.update_item(Key=key, UpdateExpression='SET state_json = :state',
                                  ExpressionAttributeValues={':state': json.dumps(state)})
            def invoke(body):
                from execution_identity import sign_grant, execution_secret
                secret = credentials()
                actor = body.get('actor', {})
                runtime_user, identity_kind = runtime_identity(body, secret)
                user_id = runtime_user or 'service:gtm-backend'
                tools = {'call-review': ['crm-tools___filter_findings', 'crm-tools___commit_sales'],
                         'meeting-prep': ['crm-tools___get_opportunity']}[body['skill_id']]
                grant = {'user_id': user_id, 'team_id': actor.get('team_id', 'service'), 'skill_id': body['skill_id'],
                         'opportunity_id': body['opportunity_id'], 'request_id': body['request_id'],
                         'expires_at': int(time.time()) + 180, 'allowed_tools': tools}
                body = {**body, 'authorization': sign_grant(grant, execution_secret()),
                        'identity': {'kind': identity_kind, 'user_id': user_id}}
                session_id = 'gtm-' + hashlib.sha256(body['request_id'].encode()).hexdigest()
                reply = runtime.invoke_agent_runtime(agentRuntimeArn=os.environ['RUNTIME_ARN'], qualifier='demo',
                    runtimeSessionId=session_id, contentType='application/json', payload=json.dumps(body).encode(),
                    **({'runtimeUserId': runtime_user} if runtime_user else {}))
                result = json.loads(reply['response'].read())
                if isinstance(result, str): result = json.loads(result)
                return result
            execute_job(payload, stored, invoke, save, slack_post)
            table.update_item(Key=key, UpdateExpression='SET lease_until = :zero, job_status = :status',
                              ExpressionAttributeValues={':zero': 0, ':status': 'completed'})
            print(json.dumps({'event': 'gtm_job_completed', 'request_id': payload['request_id'], 'source': payload.get('source'),
                              'skill_id': payload['skill_id'], 'latency_ms': (int(time.time()) - now) * 1000}))
        except Exception as error:
            detail = getattr(error, 'response', {}).get('Error', {})
            print(json.dumps({'event': 'gtm_job_failed', 'request_id': payload['request_id'], 'error_type': type(error).__name__,
                              'error_code': detail.get('Code'), 'operation': getattr(error, 'operation_name', None),
                              'message': detail.get('Message', str(error))[:400]}))
            failures.append({'itemIdentifier': record['messageId']})
    return {'batchItemFailures': failures}
