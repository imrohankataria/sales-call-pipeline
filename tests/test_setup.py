"""Run onboarding against private temporary files; no accounts or network calls."""

import json
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TEMPLATE = '''AWS_PROFILE=
AWS_REGION=
SLACK_BOT_TOKEN=
SLACK_SIGNING_SECRET=
SLACK_APP_TOKEN=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
'''


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'scripts').mkdir()
        script = Path(__file__).resolve().parents[1] / 'scripts/check_setup.py'
        if script.exists():
            shutil.copy(script, self.root / 'scripts/check_setup.py')
        (self.root / '.env.example').write_text(TEMPLATE)
        (self.root / 'config.example.json').write_text(json.dumps({'aws_profile': 'team-demo', 'aws_region': 'us-east-2'}))

    def run_setup(self, *args):
        return subprocess.run([sys.executable, str(self.root / 'scripts/check_setup.py'), *args], capture_output=True, text=True)

    def test_initialization_creates_private_files_and_needs_no_local_keys(self):
        result = self.run_setup('--init', '--mode', 'local')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / '.env').read_text(), TEMPLATE)
        self.assertEqual(json.loads(result.stdout)['state'], 'configuration_ready')
        self.assertEqual(stat.S_IMODE((self.root / '.env').stat().st_mode), 0o600)
        self.assertTrue((self.root / 'config.local.json').exists())

    def test_initialization_preserves_filled_fields_without_printing_them(self):
        private = 'SLACK_BOT_TOKEN=private-test-value\n'
        (self.root / '.env').write_text(private)
        result = self.run_setup('--init', '--mode', 'local')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / '.env').read_text(), private)
        self.assertNotIn('private-test-value', result.stdout + result.stderr)

    def test_aws_configuration_is_blocked_until_profile_and_region_are_filled(self):
        result = self.run_setup('--init', '--mode', 'aws')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['missing'], ['AWS_PROFILE', 'AWS_REGION'])

    def test_filled_aws_configuration_does_not_claim_live_authentication(self):
        self.run_setup('--init')
        (self.root / '.env').write_text('AWS_PROFILE=team-demo\nAWS_REGION=us-east-2\n')
        result = self.run_setup('--mode', 'aws')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['state'], 'configuration_ready')
        self.assertEqual(report['authentication'], 'not_verified')

    def test_aws_region_mismatch_is_blocked(self):
        self.run_setup('--init')
        (self.root / '.env').write_text('AWS_PROFILE=team-demo\nAWS_REGION=us-west-2\n')
        result = self.run_setup('--mode', 'aws')
        self.assertEqual(result.returncode, 1)
        self.assertIn('aws_configuration_mismatch', json.loads(result.stdout)['problems'])

    def test_socket_mode_only_requires_its_selected_tokens(self):
        self.run_setup('--init')
        (self.root / '.env').write_text('SLACK_BOT_TOKEN=private-bot-value\nSLACK_APP_TOKEN=private-app-value\n')
        result = self.run_setup('--mode', 'slack-socket')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('private-bot-value', result.stdout + result.stderr)
        self.assertNotIn('private-app-value', result.stdout + result.stderr)

    def test_invalid_env_content_is_not_echoed(self):
        self.run_setup('--init')
        (self.root / '.env').write_text('private-value-without-assignment\n')
        result = self.run_setup()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('private-value-without-assignment', result.stdout + result.stderr)
        self.assertIn('invalid_env_format', json.loads(result.stdout)['problems'])

    def test_static_aws_credentials_are_blocked_without_echoing_values(self):
        self.run_setup('--init')
        (self.root / '.env').write_text('AWS_ACCESS_KEY_ID=private-aws-value\n')
        result = self.run_setup()
        self.assertEqual(result.returncode, 1)
        self.assertIn('use_aws_cli_credentials', json.loads(result.stdout)['problems'])
        self.assertNotIn('private-aws-value', result.stdout + result.stderr)

    def test_only_the_selected_api_runner_needs_a_key(self):
        result = self.run_setup('--init', '--runner', 'anthropic-api')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['missing'], ['ANTHROPIC_API_KEY'])
        (self.root / '.env').write_text('ANTHROPIC_API_KEY=private-runner-value\n')
        result = self.run_setup('--runner', 'anthropic-api')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('private-runner-value', result.stdout + result.stderr)
