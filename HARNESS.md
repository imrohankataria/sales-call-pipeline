# Coding harness entry point

Include `AGENTS.md` and `docs/setup.md` in this repository's task context, then
use `prompts/setup-first.md` as the initial task. Complete the selected account,
credential and authentication prerequisites before deployment or integration.

Pause at human sign-in/consent steps and resume after the human completes them.
Keep secrets out of model context and report field presence or verification
status only. Existing Claude/Codex login can be reused; API-based harnesses can
use the corresponding private `.env` key after the user selects that route.

This file is for a coding/orchestration harness. It does not configure the
managed Amazon Bedrock AgentCore Harness service. This package hosts its own
Python workflow in AgentCore Runtime.
