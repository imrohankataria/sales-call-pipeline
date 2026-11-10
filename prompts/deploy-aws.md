# Copyable AWS deployment prompt

```text
Prepare and deploy the cloud version of this synthetic Sales Call Pipeline portable package.

Repository: https://github.com/imrohankataria/sales-call-pipeline
Configuration: config.local.json, created from config.example.json
Authentication: my existing AWS CLI login/SSO profile; no static access keys

Read AGENTS.md, README.md and docs/setup.md, and inspect the code before changing
anything. Complete setup first: create private .env/config.local.json only if
missing, help create/reuse the selected AWS project/account, fill its profile
and verified Region, run the aws setup check, and verify CLI login/SSO.
If I selected Slack or an API coding harness, complete those prerequisites
through docs/setup.md too. Do not display secrets; unused fields stay blank.
Preserve existing authentication and completed choices. Run the local
tests, install the aws extra and rerun the offline AWS SDK/Runtime checks.
Use current AWS-authored AgentCore guidance and official documentation
retrieved through Context7 where available. Verify API/schema assumptions;
documentation retrieval alone is not deployment validation.

Read the non-secret configuration and verify the account, region, model access,
service permissions and quotas with read-only checks. Ask me to sign in through
AWS CLI/SSO if needed; never ask me to paste credentials. Check AWS free-credit
eligibility and expiry in Billing. Current Free Tier terms can restrict
AgentCore to Paid-plan accounts. Do not upgrade my account automatically.
For the new AWS experience, check AWS Settings > Billing and confirm the
project's assigned Region. Keep every Regional resource in that Region; do not
use cross-Region inference. This starter's IAM template supports in-Region
foundation models. Review the policy separately before switching model types.

Show a concise resource and cost plan before creating paid resources. Once I
approve that plan, create a dedicated encrypted/private artifact bucket and
ECR repository. Run scripts/package_tools.py, upload the tool ZIP, and deploy
infra/tools.json using infra/README.md's parameter mapping and CAPABILITY_IAM.
Include the dedicated KMS log-key charge in the cost plan. Use an immutable
digest-based object key and record its S3 version ID when available. Wait for
the IAM MCP Gateway and its configured target to be READY. Read stack outputs.

Build Dockerfile for linux/arm64, push the image to ECR, and pin its image
digest. Create an HTTP AgentCore Runtime using the stack's RuntimeRoleArn,
IAM inbound authentication, configured model and enabled skills. Set
GATEWAY_URL and GATEWAY_TARGET to the stack outputs. Set GTM_MODEL_ID,
GTM_ENABLED_SKILLS (comma-separated) and GTM_MAX_TOKENS from local configuration.
Omit custom JWT authorizerConfiguration for IAM mode; verify the current API
contract and caller permissions. Create a named Runtime
endpoint, wait for READY, and save non-secret deployment outputs ONLY in
ignored deployment.local.json. Keep .env local; do not upload it or pass its
third-party secrets as Runtime environment variables. Configure bounded log retention and appropriate
encryption using the stack's LogKeyArn; inspect existing CloudTrail coverage and add audit controls as
needed within the approved plan. Keep model output tokens bounded.

Verify the actual deployment: unsigned Runtime/Gateway requests are denied;
skills lists without invoking the model; call-review writes supported facts;
meeting-prep reads them; unsupported and conflicting facts are rejected;
Lambda rejects tool-name/operation mismatches;
replaying a request preserves its result; changed intent with that request ID
is rejected. Correlate request IDs and model usage in logs. Report observed
latency as a smoke-test sample, not p95 or an SLA. Do not claim user OAuth,
managed evaluations, Policy or Slack integration unless actually configured.

Finish with the deployed resource inventory, validation results, a rollback
method and exact teardown commands for this dedicated deployment. Do not
delete unrelated resources. Keep secrets, local credentials and personal data
out of Git, build contexts, logs, prompts and model messages.
Ask whether to keep or clean up the newly created demo resources. An earlier
choice about another deployment does not determine this deployment's cleanup.
```
