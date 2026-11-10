"""Configure and verify the signed Slack pipeline without printing credentials."""
import argparse
import hashlib
import hmac
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from pipeline_deploy import ROOT, configuration, read_state, save, session_for

def post(url, data, headers):
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            return e.code, {'error': 'http_error'}

def slack_api(method, token, payload=None):
    status, data = post('https://slack.com/api/' + method,
        json.dumps(payload or {}).encode(),
        {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json; charset=utf-8'})
    if status != 200 or not data.get('ok'):
        raise ValueError('Slack ' + method + ': ' + data.get('error', 'http_error'))
    return data

def validate_settings(env):
    required = ['SLACK_BOT_TOKEN', 'SLACK_SIGNING_SECRET', 'SLACK_TEAM_ID',
                'SLACK_USER_ID', 'SLACK_TEST_CHANNEL_ID']
    missing = [k for k in required if not env.get(k)]
    if missing:
        raise ValueError('Fill private .env fields: ' + ', '.join(missing))
    for key, prefix in [('SLACK_TEAM_ID', 'T'), ('SLACK_USER_ID', '[UW]'), ('SLACK_TEST_CHANNEL_ID', '[CG]')]:
        if not re.fullmatch(prefix + r'[A-Z0-9]{5,29}', env[key]):
            raise ValueError('Invalid private identifier in ' + key)
    auth = slack_api('auth.test', env['SLACK_BOT_TOKEN'])
    if auth['team_id'] != env['SLACK_TEAM_ID']:
        raise ValueError('Slack token belongs to a different workspace')
    grants = json.loads(env.get('SLACK_SKILL_GRANTS') or
        json.dumps({env['SLACK_USER_ID']: ['call-review', 'meeting-prep']}))
    if not isinstance(grants, dict) or env['SLACK_USER_ID'] not in grants:
        raise ValueError('SLACK_SKILL_GRANTS must grant the selected member explicitly')
    for user, skills in grants.items():
        if not re.fullmatch(r'[UW][A-Z0-9]{5,29}', user) or not isinstance(skills, list) or not set(skills) <= {'call-review', 'meeting-prep'}:
            raise ValueError('Invalid member or skill in private grants')
    return {'bot_token': env['SLACK_BOT_TOKEN'], 'signing_secret': env['SLACK_SIGNING_SECRET'],
            'team_id': env['SLACK_TEAM_ID'], 'allowed_users': list(grants), 'skill_grants': grants}

def manifest(state):
    return {'display_information': {'name': 'Sales Call Pipeline',
            'description': 'Checked call facts and shared meeting preparation'},
        'features': {'bot_user': {'display_name': 'Sales Call Pipeline', 'always_online': False},
            'slash_commands': [{'command': '/gtm', 'url': state['gtm']['SlackUrl'],
                'description': 'List skills, review a call, or prepare a meeting',
                'usage_hint': 'skills | call-review demo-ID | transcript | meeting-prep demo-ID',
                'should_escape': False}]},
        'oauth_config': {'scopes': {'bot': ['commands', 'chat:write']}},
        'settings': {'socket_mode_enabled': False, 'org_deploy_enabled': False}}

def signed_request(url, secret, user, channel, text, trigger):
    raw = urllib.parse.urlencode({'team_id': secret['team_id'], 'user_id': user,
        'command': '/gtm', 'channel_id': channel, 'text': text, 'trigger_id': trigger}).encode()
    timestamp = str(int(time.time()))
    signature = 'v0=' + hmac.new(secret['signing_secret'].encode(),
        b'v0:' + timestamp.encode() + b':' + raw, hashlib.sha256).hexdigest()
    return post(url, raw, {'Content-Type': 'application/x-www-form-urlencoded',
        'X-Slack-Request-Timestamp': timestamp, 'X-Slack-Signature': signature})

def verify(config, state, secret, env, session, send):
    checks = []
    def check(name, passed, detail=None):
        checks.append({'name': name, 'passed': bool(passed), 'detail': detail})
    code, response = post(state['gtm']['SlackUrl'], b'command=%2Fgtm&text=skills',
                          {'Content-Type': 'application/x-www-form-urlencoded'})
    check('unsigned_ingress_denied', code == 401)
    runtime_url = ('https://bedrock-agentcore.' + config['aws_region'] + '.amazonaws.com/runtimes/'
        + urllib.parse.quote(state['runtime']['RuntimeArn'], safe='') + '/invocations?qualifier=demo')
    code, _ = post(runtime_url, b'{}', {'Content-Type': 'application/json'})
    check('unsigned_runtime_denied', code in (401, 403))
    code, _ = post(state['gtm']['GatewayUrl'],
        b'{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}',
        {'Content-Type': 'application/json'})
    check('unsigned_gateway_denied', code in (401, 403))
    code, directory = signed_request(state['gtm']['SlackUrl'], secret, env['SLACK_USER_ID'],
        env['SLACK_TEST_CHANNEL_ID'], 'skills', 'probe-' + uuid.uuid4().hex)
    check('private_skill_directory', code == 200 and directory.get('response_type') == 'ephemeral'
          and all(s in directory.get('text', '') for s in secret['skill_grants'][env['SLACK_USER_ID']]))
    unknown = 'U' + uuid.uuid4().hex[:12].upper()
    code, denial = signed_request(state['gtm']['SlackUrl'], secret, unknown,
        env['SLACK_TEST_CHANNEL_ID'], 'skills', 'probe-' + uuid.uuid4().hex)
    check('ungranted_member_denied', code == 200 and 'not authorized' in denial.get('text', ''))
    jobs = session.resource('dynamodb').Table(state['gtm']['JobsTable'])
    if send:
        opportunity = 'demo-retest-' + uuid.uuid4().hex[:12]
        for skill, text in [('call-review', 'The stage is Proposal. The renewal date is 2027-02-01. The contract amount is USD 24000.'),
                            ('meeting-prep', '')]:
            trigger = 'retest-' + uuid.uuid4().hex
            command = skill + ' ' + opportunity + (' | ' + text if text else '')
            code, ack = signed_request(state['gtm']['SlackUrl'], secret, env['SLACK_USER_ID'],
                env['SLACK_TEST_CHANNEL_ID'], command, trigger)
            check(skill + '_queued_privately', code == 200 and ack.get('response_type') == 'ephemeral' and 'Queued' in ack.get('text', ''))
            request_id = 'slack-' + trigger
            deadline = time.monotonic() + 180
            stored = {}
            while time.monotonic() < deadline:
                item = jobs.get_item(Key={'request_id': request_id}, ConsistentRead=True).get('Item', {})
                stored = json.loads(item.get('state_json', '{}'))
                if stored.get('slack_ts') and item.get('job_status') == 'completed':
                    break
                time.sleep(3)
            result = stored.get('result', {})
            check(skill + '_completed', result.get('status') == 'completed')
            check(skill + '_slack_delivery_receipt', bool(stored.get('slack_ts')))
            check(skill + '_runtime_user_bound', result.get('identity', {}).get('user_id') ==
                  'slack:' + secret['team_id'] + ':' + env['SLACK_USER_ID'])
            trace = [x['tool'] for x in result.get('tool_trace', [])]
            check(skill + '_mcp_trace', ('crm-tools___commit_sales' in trace if skill == 'call-review'
                  else trace == ['crm-tools___get_opportunity']))
            container = result.get('sales_result' if skill == 'call-review' else 'context', {})
            check(skill + '_shared_facts_match', container.get('crm_fields') == {
                'stage': 'Proposal', 'amount': 24000, 'renewal_date': '2027-02-01'})
            if not all(x['passed'] for x in checks):
                break
    report = {'status': 'PASS' if all(x['passed'] for x in checks) else 'FAIL', 'checks': checks,
        'scope': 'Signed HTTP replay with real AWS workflow and bot delivery' if send else 'Read-only Slack auth and signed ingress directory/denial probes; no bot messages',
        'slack_browser_installation': 'Not established by HTTP replay. Verify the actual /gtm Request URL, scopes, installation and a command sent through Slack UI.',
        'fresh_deployment': state.get('status', 'See private deployment state')}
    save(ROOT / '.local/pipeline-verification.json', report)
    print(json.dumps(report, indent=2))
    if report['status'] != 'PASS':
        raise RuntimeError('Live pipeline verification failed; inspect private job and CloudWatch evidence')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['manifest', 'auth', 'configure', 'verify'])
    p.add_argument('--config', type=Path, default=ROOT / 'config.local.json')
    p.add_argument('--state', type=Path, default=ROOT / 'deployment.local.json')
    p.add_argument('--approve', action='store_true', help='Authorize private Slack secret and member-grant update')
    p.add_argument('--send-tests', action='store_true', help='Send two labeled test workflow results to the selected demo channel')
    a = p.parse_args()
    config, env = configuration(a.config)
    session, client = session_for(config)
    account = client('sts').get_caller_identity()['Account']
    state = read_state(a.state, config, account)
    if 'gtm' not in state:
        p.error('Deploy AWS first or supply verified existing dedicated deployment state')
    if a.action == 'manifest':
        save(ROOT / '.local/slack-app-manifest.json', manifest(state))
        print('Private Slack app manifest written to .local/slack-app-manifest.json')
        return
    secret = validate_settings(env)
    if a.action == 'auth':
        print(json.dumps({'slack_authentication': 'verified', 'workspace_match': True}))
    elif a.action == 'configure':
        if not a.approve:
            p.error('Confirm the selected Slack workspace, app and member grants before --approve')
        client('secretsmanager').put_secret_value(SecretId=state['gtm']['SlackSecretArn'],
                                                  SecretString=json.dumps(secret))
        print('Private Slack secret and explicit member grants saved; no messages sent')
    else:
        deployed = json.loads(client('secretsmanager').get_secret_value(
            SecretId=state['gtm']['SlackSecretArn'])['SecretString'])
        if any(deployed.get(k) != secret[k] for k in secret):
            raise ValueError('Private local Slack settings differ from deployed grants; verify before testing')
        verify(config, state, secret, env, session, a.send_tests)

if __name__ == '__main__':
    main()
