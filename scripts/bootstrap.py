"""Create a portable local environment, install the package and run its checks."""
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    uv = shutil.which('uv')
    if not uv:
        raise RuntimeError('Install uv from https://docs.astral.sh/uv/getting-started/installation/ first')
    python = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        subprocess.run([uv, 'venv', '--python', '3.12', '--seed', str(ROOT / '.venv')], check=True)
    subprocess.run([uv, 'pip', 'install', '--python', str(python), '.[aws]'], cwd=ROOT, check=True)
    env = {**os.environ, 'PYTHONPATH': str(ROOT / 'src'), 'AWS_EC2_METADATA_DISABLED': 'true',
           'AWS_DEFAULT_REGION': 'us-east-2'}
    # Install a wheel instead of editable .pth wiring; source remains editable via PYTHONPATH.
    for args in [['scripts/check_setup.py', '--init', '--mode', 'local'],
                 ['-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                 ['-m', 'gtm_starter']]:
        subprocess.run([str(python), *args], cwd=ROOT, env=env, check=True)
    env['PYTHONPATH'] = str(ROOT / 'reference/slack-agentcore/src')
    subprocess.run([str(python), '-m', 'unittest', 'discover', '-s',
                    'reference/slack-agentcore/tests', '-v'], cwd=ROOT, env=env, check=True)
    print('Local package and Slack-reference offline checks passed. AWS/Slack live status is unverified.')

if __name__ == '__main__':
    main()
