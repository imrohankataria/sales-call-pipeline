# Accounts, keys and authentication first

Codex reads [AGENTS.md](../AGENTS.md); Claude imports it through
[CLAUDE.md](../CLAUDE.md). Other coding harnesses use
[HARNESS.md](../HARNESS.md) and the [setup prompt](../prompts/setup-first.md).

## Prepare Python and create the private setup files

Start with [the local setup prompt](../prompts/02-local.md). After uv is installed,
the harness runs `uv run --no-project --python 3.12 python scripts/bootstrap.py`.
It prepares the environment before invoking any Python setup command.

```bash
python scripts/check_setup.py --init --mode local
```

This creates `.env` from [the blank template](../.env.example) and
`config.local.json` from the configuration example, without overwriting either.
New files use owner-only permissions. Open `.env` in the local editor and fill
only the fields for the selected route. Keep all template values blank.

| Selected route | Required setup |
|---|---|
| Local demo | Python and the package; `.env` may remain blank |
| AWS deployment | AWS project/account, named CLI profile and verified Region |
| Slack HTTP extension | Slack workspace/app, bot token and signing secret |
| Slack Socket Mode extension | Slack workspace/app, bot token and app-level token |
| Optional API coding harness | Selected provider account and its API key |

The file uses literal `KEY=value`, optionally surrounded by matching quotes.
The checker never executes it, exports variables or prints their values.
The portable workflow does not automatically load `.env`; AWS uses its standard
credential chain. The supplied `pipeline_deploy.py` and `pipeline_slack.py` helpers
read this file as literal private configuration, without executing it or echoing
values. Slack/API-runner fields are only used on the selected route. A key in a
file is not a working integration.

## AWS: reuse or create, then sign in

1. Reuse the intended AWS project/account and named CLI profile. If one is
   missing, guide the user through [AWS signup](https://aws.amazon.com/).
   The user completes identity, verification, billing and terms in that UI.
   Avoid creating another project when an appropriate one already exists.
2. Verify the project's assigned Region. For the new AWS experience, use
   [AWS Settings](https://settings.aws.com/) → View all projects → Overview →
   Additional Info → Region. Check plan access, credit balance/expiry and spend
   status in AWS Settings/Billing. Do not upgrade automatically.
3. Put the selected profile and Region in `AWS_PROFILE` and `AWS_REGION` in
   `.env`, and match `aws_profile` and `aws_region` in `config.local.json`.
   Do not store AWS access keys, session tokens or passwords in `.env`.
4. Check the local CLI version and existing authentication first. The following
   uses the example profile `demo`; substitute the verified selected profile:

   ```bash
   aws --version
   aws sts get-caller-identity --profile demo
   ```

   Capture identity privately, confirm it belongs to the intended project and
   report a match/mismatch. Keep actual identifiers out of shared files.
5. If sign-in is needed, use `aws login --profile demo` for console sign-in
   identities; this requires AWS CLI 2.32.0+. Preserve an established IAM
   Identity Center flow with `aws sso login --profile demo` instead. If its
   SSO profile is missing, configure it from the organization's provided SSO
   details. Guide the user through the browser and verify identity again.
6. Check model/AgentCore access and permissions read-only. All Regional
   application resources must use the verified project Region. Sign-in does
   not establish permission, credits or deployment readiness.

The assistant should run an already authorized sign-in flow, then let the
human finish browser authentication and MFA. Reuse successful authentication.
Use the [CLI sign-in guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html),
[SSO guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)
and [CLI installation guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
when prerequisites are missing. Never ask for a password or key in the chat.

## Slack: workspace, app, tokens, then verification

Slack is optional. The portable package does not include its adapter. The included
[AWS/Slack reference](../reference/slack-agentcore/README.md) contains the signed
ingress and worker code shown in the video, with deployable infrastructure and
private grant/verification helpers. Use [the Slack prompt](../prompts/04-slack.md)
and [helper guide](prompt-deployment.md). The steps below explain the provider UI.

1. Reuse the intended workspace and app. If missing, help create a workspace at
   [Slack](https://slack.com/get-started), then create an app **From scratch**
   in [Your Apps](https://api.slack.com/apps) for that workspace. The user
   completes account verification and any required administrator consent.
2. Choose HTTP or Socket Mode and the desired interaction before requesting
   scopes. Use `chat:write` only for the intended replies. Add `commands` for
   a slash command, or `app_mentions:read` for an app-mention workflow, as
   needed. Do not request workspace-wide history or user tokens by default.
3. In **OAuth & Permissions**, configure the selected bot scopes and install
   the app in the workspace. Put its Bot User OAuth Token in `SLACK_BOT_TOKEN`.
   For HTTP, copy the signing secret from **Basic Information → App Credentials**
   directly into `SLACK_SIGNING_SECRET`.
4. For Socket Mode, create an app-level token under **Basic Information** with
   `connections:write`, put it in `SLACK_APP_TOKEN`, and enable **Socket Mode**.
   No public Request URL is needed for that transport. HTTP needs a real,
   implemented endpoint that verifies signatures before handling requests.
5. Verify the bot token using Slack's read-only `auth.test` through a private
   SDK/API request. Keep the token out of command arguments and tool output;
   report success or an error code. Check selected app scopes and transport
   settings in the app UI. Do not send messages or invite users for this check.
6. Set `SLACK_TEAM_ID`, `SLACK_USER_ID`, `SLACK_TEST_CHANNEL_ID` and optional
   `SLACK_SKILL_GRANTS` privately. Generate the app manifest with the helper,
   confirm the selected permissions and secret storage, then run its `configure`
   action. The supplied route is HTTP; Socket Mode remains an optional extension.
   Record authentication as verified only after those checks. Configure and
   test the selected ingress, user mapping and tool access before claiming a
   functioning Slack workflow. Add OAuth callback/token storage and consent
   handling separately if distributing the app across workspaces;
   `SLACK_CLIENT_ID`/`SLACK_CLIENT_SECRET` are reserved for that extension.

See [Slack app setup](https://docs.slack.dev/tools/bolt-python/creating-an-app/),
[request verification](https://docs.slack.dev/authentication/verifying-requests-from-slack/)
and [auth.test](https://docs.slack.dev/reference/methods/auth.test/).

## Claude, Codex and API-based harnesses

Reuse the tool's normal account login when available. Guide account creation
and the built-in sign-in flow if missing. Normal Claude/Codex login does not
require the two API key slots in `.env`.

If the user selects an API-based harness, help create/reuse the corresponding
developer account at the [Anthropic Console](https://console.anthropic.com/)
or [OpenAI Platform](https://platform.openai.com/), obtain the selected API key,
and enter it privately in `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`. Check that
provider's current billing/access requirements before an API call. These keys
are for the coding harness, not the starter's Bedrock Converse calls.

## Verify before proceeding

```bash
python scripts/check_setup.py --mode aws
python scripts/check_setup.py --mode slack-http
python scripts/check_setup.py --mode slack-socket
python scripts/check_setup.py --mode local --runner anthropic-api
# Or select --runner openai-api for that API harness.
```

Run only the relevant commands. The checker reports missing names and exits
with code 1 when blocked. `configuration_ready` means required fields are
present; `authentication: not_verified` still requires the live checks above.
Leave unused fields blank. Report setup, authentication and actual integration
status separately, then continue with local development or the deployment
prompt. The human completes secrets, sign-in and consent; the assistant carries
the remaining setup steps forward without repeating completed questions.

Filled `.env` stays local and ignored. For a deployed third-party integration,
use appropriate service secret storage/credential providers. Never upload the
file into the Runtime image or put secrets in Runtime configuration.
