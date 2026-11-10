# Package review

This is a synthetic educational starter. The local workflow and cloud adapters
are implemented; cloud deployment and production behavior require separate validation.

## GitHub preparation checks

The GitHub publication includes the portable package and the separate source
behind the AWS/Slack product demo. The current portable source and installed
wheel passed all 54 offline checks with the AWS extra, and the copied Slack
reference passed 36 offline checks. The installed local demo completed.
CI runs both suites without AWS credentials or Slack delivery.

The source-provenance manifest verifies all 22 copied reference files. The
only behavior change replaces the original S3 owner identifier with required
configuration. Documentation links and the exact uploaded video checksum were
checked. A publication-file pattern scan found no credentials, private paths
or known deployment identifiers; pattern matching has limits.

The 96-second video is included in `docs/media`, with captions and a compact
verification receipt. Private setup files, raw recordings, model weights and
live deployment evidence are excluded. See [the video walkthrough](video-walkthrough.md)
for the implemented scope and its differences from the portable package.

## Corrections

- Reject overprecise amounts instead of accepting a truncated integer.
- Validate requests before cloud setup; meeting prep uses no model client.
- Bind Lambda operations to Gateway's tool context and configured target.
- Validate MCP response IDs, JSON/SSE envelopes and returned fact shapes.
- Refuse redirects for signed Gateway requests; return bounded failure codes.
- Close SQLite connections and correlate model-usage logs with request IDs.
- Exclude incidental JSON, notes and local credentials from packaging/build inputs.

## Verification

Run `python -m unittest discover -s tests -v` after the README's editable install.
The dependency-free layer checks evidence, request validation, snapshots,
replay, tool routing and ZIP contents. Installing `.[aws]` enables additional
offline checks of Runtime behavior, the Bedrock Converse request, signed MCP
transport, atomic DynamoDB writes and a concurrent duplicate request. These use
synthetic responses; they do not invoke AWS.

For this unreleased `0.1.0` package, the fresh source-ZIP install passed all
45 checks with the aws extra. The base install passed 30 and skipped the 15
optional AWS checks. The installed wheel's demo and local HTTP checks passed;
CloudFormation lint passed in `us-east-2`. The source ZIP, source tarball,
wheel and Lambda ZIP had no matches in the credential/identifier-pattern scan.

Release checks also include a fresh source-ZIP install, installed-wheel demo,
local HTTP `/ping` and `/invocations`, CloudFormation lint in `us-east-2`, archive
contents and a credential/identifier-pattern scan. A scan has pattern limits and
does not guarantee arbitrary added source files contain no secrets.

The setup-first addition supplies a blank `.env.example`, creates private
`.env`/configuration without overwriting them, and gives Codex/Claude/harness
instructions for account creation and authentication. Its checker has nine
offline cases for missing fields, private output, selected routes and existing
file preservation. Filled fields do not establish live authentication; no new
AWS or Slack account was created or authenticated by this packaging update.

## Remaining deployment checks

- Build and run the ARM64 image; Docker was unavailable during this review.
- Verify project Region, plan access, credits, model access and permissions.
- Deploy the dedicated stack and Runtime, then test signed/unsigned access,
  actual Gateway tool context, replay and failure behavior, logs and cleanup.
- Measure latency and load behavior before claiming p95 or an SLA.

Evidence matching recognizes only three exact synthetic phrases. Proposed
findings can omit supported fields, and each accepted review replaces the
snapshot. Replays can rerun extraction; write protection lasts while the ledger
record remains. DynamoDB TTL is eventual. Concurrent distinct reviews use the
last committed snapshot; there is no chronological ordering or optimistic version check.

Skill enablement is configuration. Slack ingress, user grants, enterprise OAuth,
managed Policy/Evaluations and a durable queue remain extensions. Meeting prep
formats saved facts deterministically; it does not run the SKILL.md through a model.

AWS references checked for the boundaries:
[Runtime permissions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html),
[Gateway protocols](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-using.html),
[Lambda tool context and naming](https://github.com/awslabs/agentcore-samples/blob/main/03-integrations/vector-stores/elasticsearch/01-gateway-target-lambda-elasticsearch.ipynb),
and [SDK workload-token propagation](https://github.com/aws/bedrock-agentcore-sdk-python/blob/main/src/bedrock_agentcore/_utils/identity_propagation.py).

Three copied dependency files also have redundant trailing blank lines removed.
