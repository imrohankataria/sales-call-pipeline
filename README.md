# Sales Call Pipeline

**Keep the context from a good call. Give the next teammate what they need.**

Review a transcript, save checked opportunity facts, and prepare the next meeting
from the shared record. Python, AWS AgentCore, MCP tools and Slack, built from a
pattern in Rohan’s production experience.

[Want this in your organization? Contact Rohan for implementation help.](https://deploy.rohankataria.com)

## Watch the demo · 96 seconds

https://github.com/user-attachments/assets/29b589b2-7bbe-4c6b-8fcb-314764c5ba94

[Download MP4](docs/media/sales-call-pipeline.mp4)

[Captions](docs/media/sales-call-pipeline.srt) · [Video → code](docs/video-walkthrough.md)

## Start with one prompt

Open Codex, Claude Code or your coding harness in a working folder and copy:

```text
Set up https://github.com/imrohankataria/sales-call-pipeline.
Clone it into a new sales-call-pipeline folder if it is not already open.
Read AGENTS.md and follow prompts/00-start.md through all four stages:
AWS Agent Toolkit and local AWS access, local tests/demo, AWS deployment, Slack.
Reuse my accounts, named AWS profile, verified Region and suitable Slack app.
Preserve my existing work. I will complete sign-in/MFA and provider consent,
and enter secrets privately in .env; never ask for tokens in this chat.
Show the cloud resource/cost plan and wait for my approval before deployment.
Run the supplied helpers and verify the real request path, including permitted
skills, denied access, queued call review, the shared record and meeting prep.
Use my explicitly approved demo channel for test results. Record what actually
passed, explain any action I must finish, and resume afterward. Keep secrets
and deployment identifiers out of Git. Finish with a working demo and a
keep-or-clean-up choice for the dedicated resources.
```

Prefer smaller steps? Each link contains a copyable prompt:

| Step | Prompt |
|---|---|
| 1. AWS guidance and sign-in | [Install AWS Agent Toolkit](prompts/01-aws-toolkit.md) |
| 2. Local code and tests | [Run the local workflow](prompts/02-local.md) |
| 3. Deploy to AWS | [Deploy the pipeline](prompts/03-aws.md) |
| 4. Slack app and workflow | [Connect and test Slack](prompts/04-slack.md) |

The harness runs the commands. You complete account verification, MFA, billing
approval and workspace consent. Local mode needs no cloud credentials.

## Try it in Slack

```text
/gtm skills
/gtm call-review demo-001 | The stage is Proposal. The renewal date is 2027-02-01. The contract amount is USD 24000.
/gtm meeting-prep demo-001
```

The permitted task list is private. Call review queues work and replies when
checked facts are saved. Meeting prep is a separate request that reads them.

[Setup](docs/setup.md) · [Deployment helpers](docs/prompt-deployment.md) ·
[Prompt retest](docs/prompt-retest.md) · [Architecture and source](reference/slack-agentcore/README.md)

The deployed route stores three checked fields in DynamoDB. The portable local
package uses SQLite. Connectors for calling software and Salesforce are future
extensions; the current source and acceptance checks define this repo’s behavior.
