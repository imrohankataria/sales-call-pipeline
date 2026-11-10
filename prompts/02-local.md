# 2. Run the local workflow

```text
Prepare and run this repository locally. Read AGENTS.md. Detect/install uv from
its official source, then run:
uv run --no-project --python 3.12 python scripts/bootstrap.py
This creates a Python environment if missing, installs the pinned AWS dependencies
including botocore[crt] for AWS CLI browser-login profiles,
initializes private setup files, runs both test suites, and runs the local demo.
Use the platform-specific .venv Python path for later helpers. Do not execute .env
as a shell script. Preserve filled fields and leave unused tokens blank.
The bootstrap installs a wheel rather than relying on editable .pth imports;
for source development use PYTHONPATH=src with the platform's syntax.
Show the saved call-review facts and how the separate meeting-prep command reads
them. Explain that SKILL.md supplies instructions, Python runs the workflow,
and tools validate access/evidence before writes. No local demo needs cloud keys.
Run python scripts/check_setup.py --mode aws once AWS fields are set. Presence is
not authentication. Report actual test/demo results and continue to prompts/03-aws.md
only when I have selected AWS deployment. Keep all secrets and local outputs ignored.
```

The local portable demo uses SQLite. The video’s deployed HTTP/Slack path uses the
separate reference workflow and DynamoDB; the next prompt deploys that exact path.
