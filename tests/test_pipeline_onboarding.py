"""Check reproducible packaging and infrastructure boundaries without AWS calls."""
import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pipeline_deploy as deploy
from pipeline_templates import templates

class OnboardingTests(unittest.TestCase):
    def test_templates_have_no_personal_ids_or_dangling_references(self):
        built = templates()
        for name, template in built.items():
            raw = json.dumps(template)
            self.assertNotRegex(raw, r'arn:aws:[^"\s]*:[0-9]{12}:')
            self.assertNotIn('rohan-gtm-demo', raw)
            defined = set(template['Resources']) | set(template['Parameters'])
            def walk(value):
                if isinstance(value, dict):
                    if 'Ref' in value:
                        self.assertTrue(value['Ref'] in defined or value['Ref'].startswith('AWS::'), value['Ref'])
                    if 'Fn::GetAtt' in value:
                        target = value['Fn::GetAtt'][0] if isinstance(value['Fn::GetAtt'], list) else value['Fn::GetAtt'].split('.')[0]
                        self.assertIn(target, defined)
                    for child in value.values(): walk(child)
                elif isinstance(value, list):
                    for child in value: walk(child)
            walk(template)
        self.assertEqual(built['gtm']['Resources']['Gateway']['Properties']['AuthorizerType'], 'AWS_IAM')
        self.assertEqual(built['gtm']['Resources']['Queue']['Properties']['VisibilityTimeout'], 720)

    def test_worker_deploys_with_ten_unreserved_executions(self):
        resources = templates()['gtm']['Resources']
        # The real fresh project has a total of 10 and must leave 10 unreserved.
        reserved = resources['WorkerFunction']['Properties'].get('ReservedConcurrentExecutions', 0)
        self.assertLessEqual(reserved, 10 - 10)
        self.assertEqual(resources['QueueMapping']['Properties']['ScalingConfig']['MaximumConcurrency'], 2)

    def test_insufficient_lambda_capacity_stops_before_state_or_cloud_changes(self):
        class ReadClient:
            def get_caller_identity(self): return {'Account': 'example-project'}
            def get_account_plan_state(self): return {'accountPlanType': 'FREE'}
            def list_agent_runtimes(self, **kwargs): return {'agentRuntimes': []}
            def get_account_settings(self):
                return {'AccountLimit': {'ConcurrentExecutions': 10, 'UnreservedConcurrentExecutions': 1}}
            def validate_template(self, **kwargs):
                raise ValueError('CloudFormation reached before capacity check')
        config = {'aws_region': 'us-east-2', 'project_name': 'pipeline-test',
                  'runtime_name': 'pipeline_test', 'model_id': 'amazon.nova-lite-v1:0'}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.json'
            with patch.object(deploy, 'session_for', return_value=(None, lambda name: ReadClient())):
                with self.assertRaisesRegex(ValueError, 'unreserved Lambda'):
                    deploy.deploy(config, path)
            self.assertFalse(path.exists())

    def test_lambda_bundle_excludes_private_incidental_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = deploy.bundle(Path(tmp), install=False)
            with zipfile.ZipFile(artifacts['lambda']) as z:
                self.assertIn('slack_handlers.py', z.namelist())
                self.assertIn('execution_identity.py', z.namelist())
                self.assertNotIn('agent_app.py', z.namelist())
                self.assertTrue(all(Path(n).suffix == '.py' for n in z.namelist()))
            with zipfile.ZipFile(artifacts['agent']) as z:
                self.assertIn('agent_app.py', z.namelist())
                self.assertIn('gateway_client.py', z.namelist())
                self.assertNotIn('.env', z.namelist())

    def test_state_cannot_cross_projects_or_regions(self):
        config = {'aws_region': 'us-east-2', 'project_name': 'pipeline-test', 'runtime_name': 'pipeline_test'}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.json'
            state = deploy.read_state(path, config, 'example-project')
            deploy.save(path, state)
            with self.assertRaises(ValueError):
                deploy.read_state(path, config, 'different-project')
            with self.assertRaises(ValueError):
                deploy.read_state(path, {**config, 'aws_region': 'us-west-2'}, 'example-project')

    def test_manifest_requests_only_command_and_reply_scopes(self):
        import pipeline_slack
        value = pipeline_slack.manifest({'gtm': {'SlackUrl': 'https://example.invalid/slack/events'}})
        self.assertEqual(value['oauth_config']['scopes']['bot'], ['commands', 'chat:write'])
        self.assertFalse(value['settings']['socket_mode_enabled'])
        self.assertEqual(value['features']['slash_commands'][0]['command'], '/gtm')

if __name__ == '__main__':
    unittest.main()
