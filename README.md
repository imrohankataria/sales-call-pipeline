# Sales Call Pipeline

**Keep the context from a good sales call. Cut the handoffs that follow.**

Turn a transcript into checked opportunity facts, a shared record and meeting prep. Built from a pattern in Rohan’s production experience.

## Watch the demo · 83 seconds

https://github.com/user-attachments/assets/67256474-a2a2-4755-af2f-759b55d771ac

[Captions](docs/media/sales-call-pipeline.srt) · [MP4](docs/media/sales-call-pipeline.mp4) · [Video → code](docs/video-walkthrough.md)

## Start with Codex

Clone the repository, open the folder in Codex, then copy a prompt below.

```bash
git clone https://github.com/imrohankataria/sales-call-pipeline.git
cd sales-call-pipeline
```

### 1. Set up accounts and keys

```text
Set up Sales Call Pipeline. Read AGENTS.md and docs/setup.md.
Create .env and config.local.json only if missing; preserve existing work.
Ask whether I want local mode or the AWS/Slack reference, unless already chosen.
Reuse my accounts, Slack app and AWS profile. Help me create anything missing
and complete sign-in. I will enter keys privately in .env and finish MFA or
provider consent in the browser. Never print secrets or ask for them in chat.
Use AWS CLI login/SSO, not static keys. Verify authentication, Region and
required permissions before integration work. Run the setup checker and report
only missing field names and the next step. Do not upgrade plans or deploy yet.
```

### 2. Run locally and extend

```text
Run Sales Call Pipeline locally. Read AGENTS.md and complete docs/setup.md.
Use Python 3.12+, create a virtual environment, install the portable package,
run its tests and python -m gtm_starter. Local mode needs no keys or AWS calls.
Preserve my existing files. Explain how call-review saves checked facts and
meeting-prep reads them. Show the skill files, Python routing and validation.
Then help me add one skill with a clear input/output contract and acceptance
checks. Keep credentials out of Git. Do not deploy as part of this task.
```

### 3. Set up the AWS/Slack workflow in the video

```text
Help me set up the AWS/Slack workflow shown in the video.
Read AGENTS.md, docs/setup.md and reference/slack-agentcore/README.md.
Inspect the reference code and reuse existing AWS resources and Slack settings.
Create private setup files only if missing. Help me fill .env privately and
verify AWS login/SSO, the assigned Region, permissions and Slack authentication.
Explain the Slack → queue → worker → AgentCore Python → model → MCP tools →
shared record → Slack reply path using this code. Meeting prep is a separate
request. Show the remaining wiring and resource/cost plan before deployment.
Do not upgrade plans, expose secrets or send Slack test messages without my
request. Distinguish existing deployment evidence from this checkout's status.
```

## Where to look

| Path | Purpose |
|---|---|
| [`src/gtm_starter`](src/gtm_starter) | Portable Python workflow, local SQLite demo and cloud adapters |
| [`reference/slack-agentcore`](reference/slack-agentcore/README.md) | AWS/Slack reference shown in the video, with its request path and configuration |
| [`SKILL.md` files](src/gtm_starter/skills) | Versioned task instructions; Python runs the workflow and tools check writes |

The portable package and AWS/Slack reference are separate paths. A fresh clone needs configuration; the reference checks three opportunity fields. Broader Salesforce and coaching examples come from Rohan’s production experience.

[Setup](docs/setup.md) · [Package guide](docs/package-guide.md) · [Portable AWS deployment](prompts/deploy-aws.md) · [Verification scope](docs/review.md)
