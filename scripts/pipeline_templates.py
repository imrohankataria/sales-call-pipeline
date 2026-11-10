"""Parameterize the deployed reference templates without personal identifiers."""
import copy
import json
from pathlib import Path
from pipeline_branding import annotate

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'reference/slack-agentcore/infra'

def templates():
    result = {n: json.loads((FOLDER / (n + '.json')).read_text())
              for n in ['foundation', 'app', 'gtm', 'app-gtm']}
    for name, template in result.items():
        template['Description'] = 'Sales Call Pipeline ' + name + ': dedicated single-Region deployment'
        template.setdefault('Parameters', {}).update({
            'PipelineName': {'Type': 'String', 'AllowedPattern': '[a-z][a-z0-9-]{2,35}'},
            'RuntimeName': {'Type': 'String', 'AllowedPattern': '[a-zA-Z][a-zA-Z0-9_]{2,47}'},
            'ModelId': {'Type': 'String', 'Default': 'amazon.nova-lite-v1:0'},
        })
        for resource in template['Resources'].values():
            tags = resource['Properties'].get('Tags')
            if isinstance(tags, dict):
                tags.update(Purpose='SalesCallPipeline')
        if name.startswith('app'):
            resources = template['Resources']
            # Keep the CRM and Runtime; the old interview practice API is not deployed.
            for key in list(resources):
                if key not in ['CrmTable', 'AgentRole', 'Runtime', 'DemoEndpoint']:
                    del resources[key]
            role_statements = resources['AgentRole']['Properties']['Policies'][0]['PolicyDocument']['Statement']
            role_statements[:] = [s for s in role_statements if 'execute-api:Invoke' not in s['Action']]
            for s in role_statements:
                if 'bedrock:InvokeModel' in s['Action']:
                    s['Resource'] = {'Fn::Sub': 'arn:${AWS::Partition}:bedrock:${AWS::Region}::foundation-model/${ModelId}'}
            runtime = resources['Runtime']
            runtime.pop('DependsOn', None)
            props = runtime['Properties']
            props['AgentRuntimeName'] = {'Ref': 'RuntimeName'}
            props['Description'] = 'Sales call review and meeting preparation'
            env = props['EnvironmentVariables']
            env.pop('EXERCISE_API_URL', None)
            env.update(AWS_REGION={'Ref': 'AWS::Region'}, AWS_ACCOUNT_ID={'Ref': 'AWS::AccountId'})
            template['Outputs'] = {k: v for k, v in template['Outputs'].items()
                                   if k in ['RuntimeArn', 'RuntimeId', 'EndpointId', 'CrmTable']}
        if name == 'foundation':
            # Versioned artifacts remain available for rollback; no seven-day code expiry.
            props = template['Resources']['Artifacts']['Properties']
            props.pop('LifecycleConfiguration', None)
            props['VersioningConfiguration'] = {'Status': 'Enabled'}
        if name == 'gtm':
            resources = template['Resources']
            template.setdefault('Metadata', {}).setdefault('AWSToolsMetrics', {})['AWSAgentToolkit'] = 'aws-cloudformation@3'
            # New projects can have only 10 total executions and must leave all
            # 10 unreserved. Bound this queue without reserving shared capacity.
            resources['WorkerFunction']['Properties'].pop('ReservedConcurrentExecutions', None)
            resources['QueueMapping']['Properties']['ScalingConfig'] = {'MaximumConcurrency': 2}
            resources['SlackSecret']['Properties']['Name'] = {'Fn::Sub': '${PipelineName}-slack'}
            resources['AuthSecret']['Properties']['Name'] = {'Fn::Sub': '${PipelineName}-execution-grants'}
            resources['Gateway']['Properties']['Name'] = {'Ref': 'PipelineName'}
            resources['Api']['Properties']['Name'] = {'Fn::Sub': '${PipelineName}-slack'}
            statements = resources['WorkerRole']['Properties']['Policies'][0]['PolicyDocument']['Statement']
            for s in statements:
                # This code uses runtimeUserId; no separate broker identity is minted.
                if 'bedrock-agentcore:GetWorkloadAccessToken' in s['Action']:
                    s['Resource'] = [{'Fn::Sub': 'arn:${AWS::Partition}:bedrock-agentcore:${AWS::Region}:${AWS::AccountId}:workload-identity-directory/default'},
                        {'Fn::Sub': 'arn:${AWS::Partition}:bedrock-agentcore:${AWS::Region}:${AWS::AccountId}:workload-identity-directory/default/workload-identity/${RuntimeName}-*'}]
    for template in result.values():
        used = json.dumps({'Resources': template['Resources'], 'Outputs': template.get('Outputs', {})})
        for key in list(template.get('Parameters', {})):
            if '"Ref": "' + key + '"' not in used and '${' + key + '}' not in used:
                del template['Parameters'][key]
    return {name: annotate(copy.deepcopy(template)) for name, template in result.items()}

if __name__ == '__main__':
    for name, value in templates().items():
        (FOLDER / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')
    print('Portable reference templates generated; no AWS calls.')
