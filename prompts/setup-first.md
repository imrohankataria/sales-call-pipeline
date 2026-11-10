# Copyable setup-first prompt

```text
Set up this Sales Call Pipeline portable package before development or deployment.

Repository: https://github.com/imrohankataria/sales-call-pipeline
Local folder: agentcore-gtm-starter

Read AGENTS.md, README.md and docs/setup.md. Preserve existing work. Establish
whether I want the local demo, AWS deployment, or AWS with a Slack extension.
Reuse any choice I have already made and require only those prerequisites.

Run python scripts/check_setup.py --init --mode local. Create the private .env
and config.local.json only if missing. Help me obtain and fill the selected
fields first. Never display .env contents or ask me to paste keys into chat.
Open the file so I can enter secrets privately; fill non-secret configuration
from verified choices and show missing field names through the checker.

Reuse existing accounts, workspaces, apps and AWS profiles. Help create a
missing selected account or Slack app in the provider UI; I will complete
passwords, verification, MFA, billing details and consent there. Authenticate
AWS using the appropriate existing named CLI login/SSO profile and temporary
credentials. Verify the project Region, plan access, credits and permissions
before any paid deployment. Do not create static AWS keys or upgrade a plan.

For Slack, choose HTTP or Socket Mode before generating tokens. Explain the
minimum scopes, guide app installation and place tokens in private .env.
Verify authentication with read-only checks. Do not post a message as a test.
Slack ingress is an extension in this starter: distinguish prepared tokens
from an implemented and verified adapter.

Reuse my Claude/Codex login. Require ANTHROPIC_API_KEY or OPENAI_API_KEY only
if I choose an API-based coding harness; neither authenticates Bedrock here.
Run the selected setup checks, local tests and demo. Report what's ready,
what was actually authenticated, and the next specific missing prerequisite.
Continue useful local work while waiting for a human sign-in step. Ask once
for information you cannot determine; preserve my answers across steps.

Use prompts/start-here.md for development or prompts/deploy-aws.md for cloud
work after setup. Keep keys and personal outputs out of Git and releases.
```
