# Copyable local development prompt

```text
Help me develop this Sales Call Pipeline portable package locally.

Repository: https://github.com/imrohankataria/sales-call-pipeline
Local folder: agentcore-gtm-starter
AWS region for a later deployment: us-east-2
Business vertical: GTM

Clone the repository into the local folder. If it already exists, inspect its
status and preserve my changes. Read AGENTS.md, README.md, docs/setup.md,
config.example.json and the skill catalog. Follow the setup-first flow: create
private .env and config.local.json only if missing, and get selected fields
filled and authentication verified before integration work. Local-only mode
needs no keys. Create a Python 3.12+ virtual environment, install the local
package, run the full test suite, and run python -m gtm_starter.

Explain the call-review → saved facts → meeting-prep flow in a few sentences.
Show me where skill instructions, workflow routing, validation and cloud
adapters live. Copy config.example.json to ignored config.local.json if it
does not exist. Keep resource names, region, model and skill selection
parameterized. Help me add one new skill at a time with a clear contract and
acceptance tests.

Use only synthetic data. Help me obtain required selected keys through their
provider UI and enter them privately in .env; never request them in chat or
commit them. Keep AWS access keys, Slack tokens and personal outputs out of
shared files. AWS authentication uses CLI login/SSO, not static keys.
Local mode requires no AWS
credentials and makes no AWS calls. Do not deploy or upgrade an AWS account
as part of this local-development task.

When I ask to deploy, use prompts/deploy-aws.md and check current AWS free
credit eligibility, expiry and AgentCore service access. Explain that credits
are conditional and AgentCore may require a Paid plan. Keep the README concise
and update its diagram when the implemented architecture changes.
```
