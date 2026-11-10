# Sales Call Pipeline: setup first

Read `README.md`, `docs/setup.md`, and any ignored `.local/aws-rules.md` before starting. Apply these instructions
to Codex, Claude and other coding harnesses working in this repository.

1. Establish the requested route: local demo, AWS deployment, or an AWS workflow
   with a Slack extension. Reuse the user's existing choice. Require only the
   accounts and credentials needed by that route.
2. Prepare uv/Python first using `prompts/02-local.md` and `scripts/bootstrap.py`;
   then run `python scripts/check_setup.py --init --mode local`. Preserve existing
   `.env`, `config.local.json`, accounts, Slack apps and AWS profiles. Open the
   private `.env` for entries; inspect presence with the checker, never by
   printing or sending its contents to the model.
3. Help create missing selected accounts/apps and complete authentication using
   `docs/setup.md`. Reuse existing accounts first. The human completes passwords,
   MFA, email verification, billing details and provider consent in the provider
   UI, and puts selected keys directly in `.env`. Continue when they return.
4. For AWS, use a named CLI login/SSO profile and temporary credentials. Match
   the profile and verified project Region in `.env` and `config.local.json`.
   Check existing authentication before starting a new login. A request to set
   up authentication authorizes that flow; avoid repeating an approval already
   given. Do not create static AWS access keys for this starter.
5. Run the checker for the selected route and API runner, then verify live
   authentication with read-only service checks. `configuration_ready` means
   fields exist, not that an account is authenticated or an integration works.
   Do not use an unverified credential in deployment or integration work.
6. Run the tests and local demo. Use `prompts/deploy-aws.md` for cloud work after
   prerequisites are verified. Present the resource/cost plan before paid
   deployment; do not upgrade plans or publish without authorization.

Keep real keys in ignored `.env` only for local development. Never put them in
`.env.example`, Git, release archives, Docker contexts, logs, model messages,
command arguments or Runtime environment configuration. Do not execute `.env`
as a shell script. Use appropriate service secret storage for a deployed
extension; the Runtime uses IAM service roles for AWS access.

For the portable package, Slack is a separate route. The source behind the video
is in `reference/slack-agentcore`, with deployable templates and helpers in
`scripts/pipeline_*.py`. Follow `prompts/00-start.md` or the four numbered prompts
for Toolkit setup, local checks, AWS deployment and Slack. Read its README and
`docs/prompt-deployment.md` before working on that route. Creating a
Slack app or filling its tokens does not implement that work. Do not send Slack
messages, invite users or post socially as an authentication check. Keep this
demo bounded to its existing demo-data contract; distinguish a prepared account, verified authentication,
implemented adapter and tested end-to-end workflow in the final status.

Limit work to this repository. Preserve user changes and unrelated projects.
