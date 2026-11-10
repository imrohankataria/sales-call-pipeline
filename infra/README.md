# Cloud infrastructure

`tools.json` creates the synthetic CRM table, validation Lambda, IAM MCP Gateway
and target, service roles, and an encrypted Lambda log group. A dedicated KMS
key encrypts logs; include its ongoing charge in your cost plan. This template
has passed local `cfn-lint` validation in `us-east-2`, but has not been deployed.

The deployment prompt creates a private S3 artifact bucket and ECR repository
first, then this stack, then an HTTP AgentCore Runtime and named endpoint. It
configures Runtime log retention and encryption using `LogKeyArn` after the
Runtime exists. No Slack app, queue, user grants or OAuth connection is created.

The template also passes `GatewayTargetName` to Lambda as `GATEWAY_TARGET`.
Lambda requires `context.client_context.custom['bedrockAgentCoreToolName']` to
match that target and the requested operation. A direct Lambda invocation with
only an `operation` argument is rejected. This is tool routing, not a user grant;
restrict direct Lambda invocation separately through IAM.

| Template parameter | Value |
|---|---|
| `ProjectName` | `project_name` from local configuration |
| `RuntimeName` | `runtime_name`; must match the Runtime created later |
| `ArtifactBucket` | Dedicated private S3 bucket in the selected Region |
| `ToolsObjectKey` | Immutable, digest-based key for `build/tools.zip` |
| `ToolsObjectVersion` | S3 object version ID, if bucket versioning is enabled |
| `EcrRepositoryName` | Dedicated repository name created before the stack |
| `GatewayTargetName` | `gateway_target` from local configuration |
| `ModelId` | `model_id`; this policy supports in-Region foundation models |
| `LogRetentionDays` | `log_retention_days` |
| `RecordTtlSeconds` | `record_ttl_seconds` |

The Lambda role can read/write only the demo table. The Gateway role can invoke
only the tool Lambda. The Runtime role can call the selected model and Gateway,
read the selected image repository and write its own Runtime logs. ECR token
access requires `Resource: "*"`; that permission does not grant repository access.
Runtime can obtain a service workload token for its own managed workload identity.
The template grants neither direct CRM access nor user-token minting to Runtime.
IAM service roles do not implement skill-level user authorization.

Deployment needs `CAPABILITY_IAM` and permission to create/pass these service
roles. The caller also needs permission to invoke the dedicated Runtime endpoint;
do not attach a broad AgentCore policy just to run the demo. Check current AWS
service availability, quota and model access before creating resources.

Keep release artifacts until the rollback window ends. Roll back by pointing the
Runtime endpoint to the previous Runtime version and restoring the matching
tool ZIP/catalog release. Teardown removes the endpoint/Runtime before this
stack, then the dedicated ECR images/repository and S3 objects/bucket. Remove
Runtime log groups before the stack's KMS key is scheduled for deletion. Stack
deletion removes synthetic CRM data; export only if intentionally needed.

Schema references: [Gateway](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-bedrockagentcore-gateway.html),
[Gateway target](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-bedrockagentcore-gatewaytarget.html),
[Runtime permissions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html).

The client pins the supported MCP `2025-03-26` handshake and sends its protocol
version on subsequent calls. It supports bounded JSON and SSE responses;
it does not implement server-initiated sampling, elicitation or long-running tasks.
# Public attribution

The template includes Rohan Kataria attribution in supported resource tags,
its description and the `ImplementationHelpUrl` output:
https://deploy.rohankataria.com. This is a contact link, not a data destination.
