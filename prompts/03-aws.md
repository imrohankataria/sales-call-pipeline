# 3. Deploy the AWS pipeline shown in the video

```text
Deploy the AWS/Slack reference pipeline from this repository. Read AGENTS.md,
docs/setup.md and docs/prompt-deployment.md. Complete prompts/01-aws-toolkit.md
and 02-local.md first. Reuse existing authorized login and assigned Region.
Verify plan/model/service access and permissions with read-only checks.
Check Lambda's total and unreserved concurrency. The queue caps workers at two;
do not reserve Lambda concurrency, increase quotas or upgrade billing silently.
Set a dedicated project_name and runtime_name in config.local.json. Preserve an
existing deployment only if its private state matches the intended project,
Region and namespace. Do not update unrelated stacks or change billing plans.
Run the .venv Python on scripts/pipeline_deploy.py plan. Explain recurring KMS,
Secrets Manager and usage costs. Show the scoped IAM/resources and bounded demo
settings. Wait for my approval of that concrete plan before creating resources.
After approval, run scripts/pipeline_deploy.py deploy --approve. This builds the
Linux ARM64 Runtime ZIP, uploads immutable code and pinned skills, provisions the
foundation/Runtime/Slack stacks, and updates Runtime with the Gateway and catalog.
It saves deployment.local.json privately. Do not paste its identifiers into Git.
Verify stack/Runtime/Gateway readiness and the actual IAM/service path; offline
tests or READY status alone are not end-to-end proof. Follow prompts/04-slack.md
to bind the app and test the user path. If a stack fails, inspect private events
and repair the cause; do not delete it automatically or broaden IAM reflexively.
Keep all Regional resources in the verified Region. No cross-Region inference.
Explain that AgentCore hosts Python, Bedrock Nova proposes facts, S3 supplies
instructions, MCP carries checked tool calls, and DynamoDB stores shared facts.
Finish with observed validation and rollback/cleanup instructions. Ask whether
to keep the new resources. Do not claim Salesforce OAuth or unlimited throughput.
```

The portable package’s container deployment remains available separately through
[deploy-aws.md](deploy-aws.md). This prompt uses direct Python ZIP deployment and
the reference implementation shown in the video.
