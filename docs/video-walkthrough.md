# From the product demo to the code

The film follows one supported amount, $50,000, through a call-review request,
a checked save and a separately requested meeting brief. The AWS/Slack source
is in [reference/slack-agentcore](../reference/slack-agentcore/README.md).
The top-level installable package is a smaller, portable implementation.

| Video layer | Responsibility | Reference source |
|---|---|---|
| Sales dialer and transcript | A rep provides the completed transcript. A calling-vendor connector is outside this repo. | Slack command input |
| Slack task list and request | Verify the signed body and permitted user/task; return `/gtm skills` immediately or enqueue selected work. | [slack_logic.py](../reference/slack-agentcore/src/slack_logic.py), [slack_handlers.py](../reference/slack-agentcore/src/slack_handlers.py) |
| Queue and worker | Claim a job, recheck access, bind the request identity and invoke Runtime. Save the result before delivery. | [slack_handlers.py](../reference/slack-agentcore/src/slack_handlers.py) |
| AgentCore Runtime | Host the application's Python entry point. Runtime does not replace the workflow logic. | [agent_app.py](../reference/slack-agentcore/src/agent_app.py) |
| Versioned SKILL.md | Load pinned S3 instructions, verify their hash and limit the tools exposed by the selected task. | [skill_catalog.py](../reference/slack-agentcore/src/skill_catalog.py), [skills](../reference/slack-agentcore/skills) |
| Python and the language model | Python coordinates the task. Nova Lite through Bedrock proposes facts and explains checked tool results. | [gtm_logic.py](../reference/slack-agentcore/src/gtm_logic.py), [agent_logic.py](../reference/slack-agentcore/src/agent_logic.py) |
| MCP and AgentCore Gateway | Give Python a standard tool-call interface. Gateway routes those calls to the registered tool Lambda. MCP is separate from Slack transport. | [gateway_client.py](../reference/slack-agentcore/src/gateway_client.py) |
| Permission and evidence checks | Independently verify the signed application grant and the supported source quote before committing. | [execution_identity.py](../reference/slack-agentcore/src/execution_identity.py), [gateway_tools.py](../reference/slack-agentcore/src/gateway_tools.py), [exercise_api.py](../reference/slack-agentcore/src/exercise_api.py) |
| Shared record | DynamoDB stores validated opportunity events. A subsequent meeting-prep request reads that context before model drafting. | `commit_sales`, `get_opportunity`, and `run_gtm` |
| Reply to Slack | Python returns to the worker; the worker saves the job result and posts with the bot token to the original channel. | `execute_job` and `slack_post` |

## What the repository demonstrates

The reference supports explicit amount, stage and renewal-date phrases,
evidence checks, request replay protection, user/task grants, queued execution
and record-backed meeting preparation. A successful write remains the tool's
decision. The model's confidence alone is not permission to save.

The broader production-experience segment describes Salesforce, intent,
next steps, call warmth and coaching. Those richer fields and integrations are
not implemented by this three-field reference. No revenue uplift or unlimited
capacity is claimed. The 1,000+ SDR scene is a scenario illustrating handoff
pressure, rather than a throughput benchmark.

## Reproducibility and limits

[Source provenance](../reference/slack-agentcore/source-provenance.json) records
checksums for the published source and the originating reference. The only
source behavior change replaces a deployment-specific S3 bucket-owner literal
with required `AWS_ACCOUNT_ID` configuration.

Original live verification took place in Rohan's existing AWS/Slack setup.
Private resource identifiers, credentials, deployment records and Slack
screenshots stay outside this repository. Local tests and GitHub CI validate
code contracts; they do not provision infrastructure or establish a production
SLA. See the reference README for deployment requirements and delivery limits.

Three copied dependency files also have redundant trailing blank lines removed.
