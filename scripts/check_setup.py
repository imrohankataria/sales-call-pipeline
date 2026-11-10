"""Create private setup files and report missing fields without showing values.

This does not sign in, load process environment variables, or contact a service.
"""

import argparse
import json
import os
import re
from pathlib import Path


REQUIRED = {
    'local': [],
    'aws': ['AWS_PROFILE', 'AWS_REGION'],
    'slack-http': ['SLACK_BOT_TOKEN', 'SLACK_SIGNING_SECRET'],
    'slack-socket': ['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN'],
}
RUNNERS = {'none': [], 'anthropic-api': ['ANTHROPIC_API_KEY'], 'openai-api': ['OPENAI_API_KEY']}


def read_env(path):
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, separator, value = line.partition('=')
        key, value = key.strip(), value.strip()
        if not separator or not re.fullmatch(r'[A-Z_][A-Z0-9_]*', key) or key in values:
            raise ValueError('invalid_env_format')
        if value.startswith(('"', "'")):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError('invalid_env_format')
            value = value[1:-1]
        # Literal values only: no shell execution, expansion or interpolation.
        values[key] = value
    return values


def filled(value):
    return bool(value) and value.upper() not in {'TODO', 'CHANGE_ME', 'REPLACE_ME'} and not (value.startswith('<') and value.endswith('>'))


def initialize(root):
    for template, destination in [('.env.example', '.env'), ('config.example.json', 'config.local.json')]:
        path = root / destination
        if path.exists():
            continue
        data = (root / template).read_bytes()
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
        with os.fdopen(fd, 'wb') as target:
            target.write(data)


def check(root, mode, runner):
    problems, values = [], {}
    env_path, config_path = root / '.env', root / 'config.local.json'
    if not env_path.exists():
        problems.append('env_missing')
    else:
        try:
            values = read_env(env_path)
        except (ValueError, UnicodeError):
            problems.append('invalid_env_format')
        except OSError:
            problems.append('env_not_readable')
    if not config_path.exists():
        problems.append('config_missing')
    if any(values.get(key) for key in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN')):
        problems.append('use_aws_cli_credentials')
    required = REQUIRED[mode] + RUNNERS[runner]
    missing = [key for key in required if not filled(values.get(key, ''))]
    if mode == 'aws' and not missing and config_path.exists():
        try:
            config = json.loads(config_path.read_text())
            if not isinstance(config, dict):
                raise ValueError('invalid_config')
            if config.get('aws_profile') != values['AWS_PROFILE'] or config.get('aws_region') != values['AWS_REGION']:
                problems.append('aws_configuration_mismatch')
        except (ValueError, OSError, UnicodeError):
            problems.append('invalid_config')
    return {
        'state': 'blocked' if missing or problems else 'configuration_ready',
        'mode': mode, 'runner': runner,
        'missing': missing, 'problems': problems,
        'authentication': 'not_required' if mode == 'local' and runner == 'none' else 'not_verified',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--init', action='store_true', help='Create missing .env and config.local.json; preserve existing files.')
    parser.add_argument('--mode', choices=REQUIRED, default='local')
    parser.add_argument('--runner', choices=RUNNERS, default='none')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        if args.init:
            initialize(root)
        result = check(root, args.mode, args.runner)
    except OSError:
        result = {'state': 'blocked', 'missing': [], 'problems': ['setup_file_error'], 'authentication': 'not_verified'}
    print(json.dumps(result, indent=2))
    return 0 if result['state'] == 'configuration_ready' else 1


if __name__ == '__main__':
    raise SystemExit(main())
