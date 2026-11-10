# 4. Set up Slack and verify the result

```text
Connect this deployed pipeline to my selected Slack workspace. Read AGENTS.md,
docs/setup.md and docs/prompt-deployment.md. Reuse the app when appropriate.
Run scripts/pipeline_slack.py manifest with the .venv Python; use the private
.local/slack-app-manifest.json to create/configure the app through Slack's UI.
Use /gtm with the deployed signed HTTP Request URL, commands and chat:write only.
Verify the manifest in Slack's UI; a provided long_description must be 174–4000
characters. If reusing an app, verify its current endpoint and deployed route
before changing anything. Record reused-app tests separately from a fresh install.
I will complete workspace signup, admin consent and installation. Ask before
changing an existing app's endpoint or expanding access. Verify the exact app,
workspace and Request URL, and invite the bot to my selected demo channel.
Open private .env for me to enter SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET directly.
Guide me to set SLACK_TEAM_ID, SLACK_USER_ID and SLACK_TEST_CHANNEL_ID privately.
Use SLACK_SKILL_GRANTS for explicit member/task permissions. Default both demo
tasks only for my selected member after I approve those grants and secret storage.
Never ask for tokens in chat, print them or put them in command arguments.
Run scripts/pipeline_slack.py auth, then configure --approve after that authorization.
Verify without bot messages first using scripts/pipeline_slack.py verify.
After I authorize two labeled results in the named demo channel, use the actual
Slack UI pair below. The helper verify --send-tests is an alternative signed HTTP
replay that also posts two results; do not run both unless I approve four results.
Check real AWS jobs, MCP traces, saved facts, identity and Slack delivery receipts.
Actually send /gtm skills through Slack and check the private permitted list;
run /gtm call-review demo-001 | The stage is Proposal. The renewal date is
2027-02-01. The contract amount is USD 24000. Check the queued acknowledgment,
completed reply and saved record. Send /gtm meeting-prep demo-001 separately and
verify that it reads those facts. Test a configured restricted member if available;
do not create or impersonate a human member just for the test. An ungranted signed
fixture can verify backend denial, but label its scope accurately.
Record actual UI and backend results in an ignored report, then summarize without
private identifiers. Report any human action still required and resume afterward.
```

Canonical interactions are `/gtm skills`, `/gtm call-review …`, and
`/gtm meeting-prep …`. Typing plain “GTM skill” is not the implemented trigger.
