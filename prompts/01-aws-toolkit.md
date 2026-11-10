# 1. Install AWS guidance and enable local AWS access

```text
Install or verify the AWS Agent Toolkit for this coding harness. Follow the current
AWS-authored instructions at https://raw.githubusercontent.com/aws/agent-toolkit-for-aws/refs/heads/main/setup-instructions/setup.md.
Detect my OS and existing uv/AWS CLI first. Install missing tools from official
sources. Use AWS CLI 2.32.0+ for browser login. Reuse existing working authentication.
Establish my named profile, AWS experience and assigned Region once, using existing
session choices where available. For the new AWS experience, confirm the Region
in AWS Settings > View all projects > Overview > Additional Info > Region.
Run aws login for that profile only if needed; preserve an existing SSO workflow.
I will finish browser sign-in/MFA. Verify identity privately with STS and report a
project match, not credentials. Check plan/service access and spend-limit status.
Do not upgrade the plan or create static AWS keys.
Configure the Toolkit with aws configure agent-toolkit --yes --region us-east-1
--profile MY_VERIFIED_PROFILE, substituting the established profile. Let me finish
its interactive wizard where required. us-east-1 is only this Toolkit endpoint;
all Regional application resources must stay in my verified project Region.
Preserve other MCP entries. Add AWS_MCP_PROXY_PROFILES to the generated aws-mcp
entry's env without changing its command or args. Keep machine-specific rules in
.local/aws-rules.md and make the harness read them; preserve repo instructions.
Verify aws agent-toolkit list-available-skills --region us-east-1 --profile
MY_VERIFIED_PROFILE. Verify the AWS MCP connection separately after restarting
the harness if required. Catalog retrieval alone is not MCP connection proof.
Use available AWS-authored service skills before AWS work; use official docs and
Context7 if those tools are unavailable, and state that limitation accurately.
Create private .env/config.local.json after prompts/02-local.md prepares Python.
Set only AWS_PROFILE and AWS_REGION there and match the configuration. Leave
other keys blank until needed. Continue to the local workflow; do not deploy yet.
```

[AWS setup instructions](https://github.com/aws/agent-toolkit-for-aws/blob/main/setup-instructions/setup.md)
· [CLI login](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html)
· [SSO](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)

An expired session pauses live verification until sign-in finishes. Installation,
CLI authentication and an MCP connection are three separate checks.
