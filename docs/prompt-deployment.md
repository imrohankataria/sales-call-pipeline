# Prompt-driven deployment

Start with [one orchestration prompt](../prompts/00-start.md), or use the four
numbered prompts in order. Each prompt tells the harness what to run, what human
action to request, and what evidence establishes success.

| Stage | Supplied helper | Proof |
|---|---|---|
| AWS tools/login | AWS vendor setup and named CLI login/SSO | CLI identity match, skill catalog and separate MCP connection check |
| Local | `scripts/bootstrap.py` | Both suites pass; call review saves facts; meeting prep reads them |
| Cloud | `scripts/pipeline_deploy.py` | Dedicated stacks, Runtime/Gateway, packaged code and pinned skills |
| Slack | `scripts/pipeline_slack.py` | Token/workspace match; explicit grants; signed request; checked result and Slack receipt |

Use Python 3.12 in `.venv`; Windows uses `.venv/Scripts/python.exe`, Unix uses
`.venv/bin/python`. The coding harness runs these commands for you:

```bash
uv run --no-project --python 3.12 python scripts/bootstrap.py
.venv/bin/python scripts/pipeline_deploy.py plan
# After approval of the resource/cost plan:
.venv/bin/python scripts/pipeline_deploy.py deploy --approve
.venv/bin/python scripts/pipeline_slack.py manifest
# After app installation and private .env entry:
.venv/bin/python scripts/pipeline_slack.py auth
# After approval of selected member grants and secret storage:
.venv/bin/python scripts/pipeline_slack.py configure --approve
.venv/bin/python scripts/pipeline_slack.py verify
# After approval of two results in the selected demo channel:
.venv/bin/python scripts/pipeline_slack.py verify --send-tests
```

`configuration_ready` only means fields are present. The verification helper
labels HTTP replays separately from a real command sent through Slack’s UI. A
previously deployed service does not prove that someone else’s clone works.

The CloudFormation templates and deploy sequence were adapted from the working
source behind the video. The deployment uses Python ZIP artifacts for Linux
ARM64. It creates the Runtime first, then the Gateway/Slack stack, then configures
the Runtime’s Gateway URL and verified S3 catalog without a circular dependency.
The worker rechecks user grants and invokes the named `demo` endpoint; the tool
Lambda independently checks the short-lived authorization envelope and evidence.

Every application resource uses the verified project Region. The AWS Agent
Toolkit’s `us-east-1` endpoint is separate. The Runtime uses IAM service roles,
and Slack credentials live in Secrets Manager. Local `.env`, manifests,
deployment inventory and test results stay ignored. The helpers do not upgrade
plans, create static AWS keys or configure Salesforce/Outreach OAuth.

The helper deliberately supports the reference’s Nova Lite model, two versioned
skills and `demo-` records. Broader business rules require acceptance checks and
a new versioned contract. Records have a 24-hour TTL; deletion is eventual.

On updates the helper saves the previous code keys, catalog key and live `demo`
Runtime version in private `deployment.local.json` history. Keep that file backed
up privately. For rollback, point the `demo` endpoint to that Runtime
version and deploy the matching tool code; verify the complete request path.
Avoid editing an already-published `SKILL.md` version in place.

To remove a dedicated deployment after the human chooses cleanup:

```bash
.venv/bin/python scripts/pipeline_cleanup.py --approve-teardown
```

This deletes the helper’s exact tagged stacks and stored demo records, empties
its dedicated artifact/audit buckets, and removes its Runtime log groups. It
checks the project, Region and namespace first. KMS deletion has a seven-day
recovery window; Secrets Manager follows its recovery policy. Do not use this
helper on the original private deployment or unrelated resources.
