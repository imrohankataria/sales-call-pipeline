"""Reproducible AWS/Slack reference deployment. Private inputs stay local."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from check_setup import read_env
from pipeline_templates import templates
from pipeline_branding import ATTRIBUTION, WEBSITE

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'reference/slack-agentcore'

def configuration(path):
    config = json.loads(path.read_text())
    env = read_env(ROOT / '.env') if (ROOT / '.env').exists() else {}
    if any(env.get(k) for k in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN']):
        raise ValueError('Use CLI login or SSO; remove static AWS credentials from .env')
    for field, key in [('aws_profile', 'AWS_PROFILE'), ('aws_region', 'AWS_REGION')]:
        if not config.get(field) or env.get(key) != config[field]:
            raise ValueError('Match ' + field + ' to ' + key + ' in private setup files')
    if not re.fullmatch(r'[a-z][a-z0-9-]{2,35}', config['project_name']):
        raise ValueError('project_name must be 3–36 lowercase letters, digits or hyphens')
    if not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]{2,47}', config['runtime_name']):
        raise ValueError('runtime_name must be 3–48 letters, digits or underscores')
    if not re.fullmatch(r'amazon\.nova-lite-v1:0', config['model_id']):
        raise ValueError('Reference is verified with in-Region amazon.nova-lite-v1:0; review before changing models')
    return config, env

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(value, f, indent=2)
        f.write('\n')
    temporary.replace(path)
    os.chmod(path, 0o600)

def bundle(output, install=True):
    output.mkdir(parents=True, exist_ok=True)
    build = output / 'agent'
    if build.exists():
        shutil.rmtree(build)
    build.mkdir()
    if install:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check',
            '--platform', 'manylinux2014_aarch64', '--implementation', 'cp', '--python-version', '3.12',
            '--only-binary=:all:', '--target', str(build),
            '-r', str(REFERENCE / 'requirements.lock.txt')], check=True)
    agent_files = ['agent_app.py', 'agent_logic.py', 'signed_api.py', 'skill_catalog.py',
                   'gtm_logic.py', 'gateway_client.py']
    for name in agent_files:
        shutil.copy2(REFERENCE / 'src' / name, build / name)
    # An explicit source allow-list prevents .env, local JSON and incidental notes leaking.
    lambda_files = ['execution_identity.py', 'agent_logic.py', 'slack_logic.py',
        'exercise_api.py', 'practice_answers.py', 'pipeline_reference.py', 'gtm_logic.py',
        'revision_reference.py', 'skill_catalog.py', 'signed_api.py', 'agent_reference.py',
        'slack_handlers.py', 'gateway_tools.py', 'support.py', 'gateway_client.py']
    for kind, files in [('agent', list(build.rglob('*'))),
                        ('lambda', [REFERENCE / 'src' / n for n in lambda_files])]:
        with zipfile.ZipFile(output / (kind + '.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
            for file in sorted(files):
                if not file.is_file() or '__pycache__' in file.parts or file.suffix == '.pyc':
                    continue
                z.write(file, file.relative_to(build) if kind == 'agent' else file.name)
    return {kind: output / (kind + '.zip') for kind in ['agent', 'lambda']}

def session_for(config):
    import boto3
    from botocore.config import Config
    # Current boto3 supports CLI browser login; its standard chain refreshes temporary credentials.
    session = boto3.Session(profile_name=config['aws_profile'], region_name=config['aws_region'])
    settings = Config(connect_timeout=5, read_timeout=35, retries={'mode': 'standard', 'max_attempts': 3})
    return session, lambda name: session.client(name, config=settings)

def read_state(path, config, account):
    value = json.loads(path.read_text()) if path.exists() else {}
    identity = {'account_id': account, 'region': config['aws_region'], 'project_name': config['project_name'],
                'runtime_name': config['runtime_name']}
    if value and any(value.get(k) != v for k, v in identity.items()):
        raise ValueError('Deployment state belongs to a different project, Region, or resource namespace')
    return {**value, **identity}

def apply(cfn, name, template, params):
    from botocore.exceptions import ClientError
    args = {'StackName': name, 'TemplateBody': json.dumps(template), 'Capabilities': ['CAPABILITY_IAM'],
            'Parameters': [{'ParameterKey': k, 'ParameterValue': str(v)} for k, v in params.items()
                           if k in template.get('Parameters', {})],
            'Tags': [{'Key': 'Purpose', 'Value': 'SalesCallPipeline'},
                     *[{'Key': key, 'Value': value} for key, value in ATTRIBUTION.items()]]}
    cfn.validate_template(TemplateBody=args['TemplateBody'])
    try:
        existing = cfn.describe_stacks(StackName=name)['Stacks'][0]
    except ClientError as e:
        if 'does not exist' not in e.response['Error']['Message']:
            raise
        existing = None
    if existing:
        if not any(t['Key'] == 'Purpose' and t['Value'] == 'SalesCallPipeline' for t in existing.get('Tags', [])):
            raise ValueError('Refusing to update an unowned stack: ' + name)
        if existing['StackStatus'] not in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
            raise ValueError('Inspect stack status before recovery; no automatic deletion: ' + existing['StackStatus'])
        try:
            cfn.update_stack(**args)
        except ClientError as e:
            if 'No updates are to be performed' not in e.response['Error']['Message']:
                raise
    else:
        cfn.create_stack(**args)
    deadline = time.monotonic() + 1200
    last = None
    while time.monotonic() < deadline:
        stack = cfn.describe_stacks(StackName=name)['Stacks'][0]
        status = stack['StackStatus']
        if status != last:
            print(name, status, flush=True)
            last = status
        if status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
            return {x['OutputKey']: x['OutputValue'] for x in stack.get('Outputs', [])}
        if status.endswith('FAILED') or 'ROLLBACK' in status:
            raise RuntimeError('Stack failed: ' + name + ' ' + status + '; inspect private CloudFormation events')
        time.sleep(5)
    raise TimeoutError('Deployment remains in progress; inspect CloudFormation before retrying')

def plan(config):
    return {'project_name': config['project_name'], 'region': config['aws_region'],
        'route': 'Signed Slack HTTP → queue → worker → AgentCore Python → MCP → DynamoDB → Slack',
        'resources': ['Private versioned artifact bucket', 'Single-Region audit trail and audit bucket',
            'KMS log key', '2 DynamoDB tables with 24-hour record TTL', 'SQS queue and dead-letter queue',
            '4 Lambda functions', 'IAM MCP Gateway and 3 tools', 'AgentCore HTTP Runtime and demo endpoint',
            '2 Secrets Manager secrets', 'HTTP API', 'Scoped service roles, bounded logs and failure alarm'],
        'ongoing_costs': 'KMS key and Secrets Manager storage; cloud/model/API/storage/log usage. Check current regional pricing and spend limit. No automatic plan upgrade.',
        'bounds': 'Nova Lite; call review: up to 3 calls, 640 output tokens each; meeting prep: 1 call, 500 output tokens; SQS worker concurrency at most 2, shared Lambda capacity with no reservation; HTTP 3 requests/second; demo- records only',
        'implementation_help': WEBSITE,
        'approval': 'Review this plan before running deploy --approve; existing namespace is preserved'}

def deploy(config, path):
    session, client = session_for(config)
    account = client('sts').get_caller_identity()['Account']
    status = client('freetier').get_account_plan_state()
    # FREE is not a blanket AgentCore denial. Verify the actual service access;
    # CloudFormation still enforces create permissions and project controls.
    client('bedrock-agentcore-control').list_agent_runtimes(maxResults=1)
    limits = client('lambda').get_account_settings()['AccountLimit']
    if limits['UnreservedConcurrentExecutions'] < 2:
        raise ValueError('At least 2 unreserved Lambda executions are needed; inspect capacity before deploying. No quota or billing changes were made.')
    capacity = {'total': limits['ConcurrentExecutions'],
                'unreserved': limits['UnreservedConcurrentExecutions'], 'queue_maximum': 2}
    print(json.dumps({'lambda_capacity': capacity, 'capacity_is_shared': True}), flush=True)
    state = read_state(path, config, account)
    state['plan_type'] = status['accountPlanType']
    state['lambda_capacity'] = capacity
    if state.get('runtime'):
        state.setdefault('history', []).append({
            'runtime': state['runtime'].copy(), 'code_keys': state.get('code_keys', {}).copy(),
            'catalog_key': state.get('catalog_key'),
            'runtime_version': client('bedrock-agentcore-control').get_agent_runtime_endpoint(
                agentRuntimeId=state['runtime']['RuntimeId'], endpointName='demo')['liveVersion']})
    state['stacks'] = [config['project_name'] + '-' + n for n in ['foundation', 'runtime', 'slack']]
    save(path, state)
    cfn = client('cloudformation')
    t = templates()
    base = {'PipelineName': config['project_name'], 'RuntimeName': config['runtime_name'], 'ModelId': config['model_id']}
    state['foundation'] = apply(cfn, state['stacks'][0], t['foundation'], base)
    save(path, state)
    files = bundle(ROOT / 'build/slack-agentcore')
    s3 = client('s3')
    keys = {}
    for kind, file in files.items():
        key = 'code/' + kind + '-' + hashlib.sha256(file.read_bytes()).hexdigest() + '.zip'
        s3.upload_file(str(file), state['foundation']['ArtifactBucket'], key,
                       ExtraArgs={'ExpectedBucketOwner': account})
        keys[kind] = key
    state['code_keys'] = keys
    args = {**base, 'ArtifactBucket': state['foundation']['ArtifactBucket'],
        'LogsKeyArn': state['foundation']['LogsKeyArn'], 'AgentCodeKey': keys['agent'], 'LambdaCodeKey': keys['lambda']}
    # On resume, preserve the Gateway configuration instead of reverting a configured Runtime.
    if state.get('gtm'):
        args.update(GatewayUrl=state['gtm']['GatewayUrl'], GatewayArn=state['gtm']['GatewayArn'],
                    SkillCatalogKey=state['catalog_key'])
    state['runtime'] = apply(cfn, state['stacks'][1], t['app-gtm'] if state.get('gtm') else t['app'], args)
    save(path, state)
    catalog = {'release': 'sales-call-pipeline-v1', 'skills': {}}
    for name, tools in {'call-review': ['crm-tools___filter_findings', 'crm-tools___commit_sales'],
                        'meeting-prep': ['crm-tools___get_opportunity']}.items():
        key = f'skills/{name}/1.0.0/SKILL.md'
        raw = (REFERENCE / key).read_bytes()
        try:
            old = s3.get_object(Bucket=args['ArtifactBucket'], Key=key, ExpectedBucketOwner=account)['Body'].read()
            if old != raw:
                raise ValueError('Publish a new skill version; a published version is immutable')
        except s3.exceptions.NoSuchKey:
            s3.put_object(Bucket=args['ArtifactBucket'], Key=key, Body=raw, ContentType='text/markdown',
                          ExpectedBucketOwner=account, IfNoneMatch='*')
        catalog['skills'][name] = {'version': '1.0.0', 'key': key,
            'sha256': hashlib.sha256(raw).hexdigest(), 'allowed_tools': tools}
    raw = json.dumps(catalog, sort_keys=True, indent=2).encode()
    state['catalog_key'] = 'skills/catalog/' + hashlib.sha256(raw).hexdigest() + '.json'
    s3.put_object(Bucket=args['ArtifactBucket'], Key=state['catalog_key'], Body=raw,
                  ExpectedBucketOwner=account, ContentType='application/json')
    ext_args = {**base, 'ArtifactBucket': args['ArtifactBucket'], 'LogsKeyArn': args['LogsKeyArn'],
        'CodeKey': keys['lambda'], 'CrmTable': state['runtime']['CrmTable'],
        'RuntimeArn': state['runtime']['RuntimeArn'], 'RuntimeId': state['runtime']['RuntimeId']}
    state['gtm'] = apply(cfn, state['stacks'][2], t['gtm'], ext_args)
    state['gtm']['GatewayUrl'] = state['gtm']['GatewayUrl'].rstrip('/')
    if not state['gtm']['GatewayUrl'].endswith('/mcp'):
        state['gtm']['GatewayUrl'] += '/mcp'
    save(path, state)
    args.update(GatewayUrl=state['gtm']['GatewayUrl'], GatewayArn=state['gtm']['GatewayArn'],
                SkillCatalogKey=state['catalog_key'])
    state['runtime'] = apply(cfn, state['stacks'][1], t['app-gtm'], args)
    logs = client('logs')
    state['runtime_log_groups'] = []
    from botocore.exceptions import ClientError
    for suffix in ['-DEFAULT', '-demo']:
        name = '/aws/bedrock-agentcore/runtimes/' + state['runtime']['RuntimeId'] + suffix
        try:
            logs.create_log_group(logGroupName=name, kmsKeyId=args['LogsKeyArn'])
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                raise
            logs.associate_kms_key(logGroupName=name, kmsKeyId=args['LogsKeyArn'])
        logs.put_retention_policy(logGroupName=name, retentionInDays=7)
        state['runtime_log_groups'].append(name)
    state['status'] = 'AWS deployed; Slack authentication and live workflow verification still required'
    save(path, state)
    print(json.dumps({'status': state['status'], 'private_state': str(path),
                      'next': 'Use prompts/04-slack.md; endpoint and secret ARNs are saved privately'}, indent=2))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['plan', 'package', 'deploy'])
    p.add_argument('--config', type=Path, default=ROOT / 'config.local.json')
    p.add_argument('--state', type=Path, default=ROOT / 'deployment.local.json')
    p.add_argument('--approve', action='store_true')
    a = p.parse_args()
    if a.action == 'package':
        files = bundle(ROOT / 'build/slack-agentcore')
        print(json.dumps({k: str(v.relative_to(ROOT)) for k, v in files.items()}, indent=2))
        return
    config, env = configuration(a.config)
    if a.action == 'plan':
        print(json.dumps(plan(config), indent=2))
    elif not a.approve:
        p.error('Review plan first; deploy requires --approve')
    else:
        deploy(config, a.state)

if __name__ == '__main__':
    main()
