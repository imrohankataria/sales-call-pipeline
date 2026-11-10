# Start everything from one prompt

Paste into Codex, Claude Code, or a coding harness with local shell/browser access.

```text
Set up https://github.com/imrohankataria/sales-call-pipeline from scratch.
Clone it into a new sales-call-pipeline folder if it is not already open.
Read AGENTS.md and follow prompts/01-aws-toolkit.md, 02-local.md, 03-aws.md,
and 04-slack.md in order. Run their supplied helpers; do not invent missing wiring.
Reuse my AWS project, named CLI profile, verified Region and Slack app if suitable.
Ask for genuinely missing choices together. Preserve existing files and credentials.
I will complete account verification, sign-in/MFA, billing and workspace consent,
and enter secrets directly in the private .env. Never request secrets in this chat.
Show the resource/cost plan before deployment and wait for my approval of that plan.
Then build the AWS pipeline, configure Slack, and verify the actual request path.
Use a named demo channel for explicitly approved test replies. Prove permitted
skill discovery, denied access, queued call review, checked shared facts, and a
separate meeting-prep request. Stop only for an action I must complete or a real
blocker; explain the exact next action and resume after it. Record verified results
separately from account setup, offline tests, HTTP replays and live Slack UI checks.
Keep every secret and deployment identifier in ignored private files.
Finish with a working demo, a short validation report, and a keep-or-clean-up choice.
```

The prompts drive the installation, implementation, deployment and tests. Account
verification, MFA, provider terms, billing approval and Slack admin consent remain
human actions. The coding harness needs shell access and a browser or connector;
a chat-only model cannot perform the deployment.
