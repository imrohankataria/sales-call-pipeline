"""Delete only this helper's recorded, tagged deployment after explicit approval."""
import argparse
import json
import time
from pathlib import Path
from pipeline_deploy import ROOT, configuration, read_state, save, session_for

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', type=Path, default=ROOT / 'config.local.json')
    p.add_argument('--state', type=Path, default=ROOT / 'deployment.local.json')
    p.add_argument('--approve-teardown', action='store_true')
    a = p.parse_args()
    if not a.approve_teardown:
        p.error('Teardown deletes this deployment and its records; explicit --approve-teardown is required')
    config, env = configuration(a.config)
    session, client = session_for(config)
    state = read_state(a.state, config, client('sts').get_caller_identity()['Account'])
    expected = [config['project_name'] + '-' + n for n in ['foundation', 'runtime', 'slack']]
    if state.get('stacks') != expected:
        raise ValueError('No matching deployment inventory; refusing deletion')
    cfn = client('cloudformation')
    from botocore.exceptions import ClientError
    def stack(name):
        try:
            return cfn.describe_stacks(StackName=name)['Stacks'][0]
        except ClientError as e:
            if 'does not exist' not in e.response['Error']['Message']:
                raise
    for name in expected:
        value = stack(name)
        if value and not any(t['Key'] == 'Purpose' and t['Value'] == 'SalesCallPipeline' for t in value.get('Tags', [])):
            raise ValueError('Stack is not tagged as owned by this helper')
    def remove(name):
        if not stack(name):
            return
        cfn.delete_stack(StackName=name)
        deadline = time.monotonic() + 1200
        while time.monotonic() < deadline:
            value = stack(name)
            if value is None:
                return
            if value['StackStatus'] == 'DELETE_FAILED':
                raise RuntimeError('Inspect failed deletion in CloudFormation: ' + name)
            time.sleep(5)
        raise TimeoutError('Deletion still in progress; inspect before retrying')
    remove(expected[2])
    remove(expected[1])
    for name in state.get('runtime_log_groups', []):
        if not name.startswith('/aws/bedrock-agentcore/runtimes/' + state['runtime']['RuntimeId']):
            raise ValueError('Unexpected log group in inventory')
        try:
            client('logs').delete_log_group(logGroupName=name)
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise
    if state.get('foundation'):
        client('cloudtrail').stop_logging(Name=state['foundation']['AuditTrailArn'])
        s3 = session.resource('s3')
        for key in ['ArtifactBucket', 'AuditBucket']:
            bucket = s3.Bucket(state['foundation'][key])
            bucket.object_versions.all().delete()
            bucket.objects.all().delete()
    remove(expected[0])
    state['teardown'] = 'Dedicated stacks deleted; KMS key deletion scheduled after seven days; Secrets Manager uses its recovery window'
    save(a.state, state)
    print(state['teardown'])

if __name__ == '__main__':
    main()
