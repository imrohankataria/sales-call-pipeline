# Prompt reproduction test

Tested in a separate Codex chat from a fresh public clone, without the original
private source or deployment artifacts. The supplied AWS helper at `96e771e`
completed a dedicated deployment and a real backend save-and-read workflow.
The resources were kept as requested. A new Slack installation remains pending.

| Check | Observed result |
|---|---|
| Supplied bootstrap | Pass; Python 3.12 and AWS dependencies installed |
| Portable/onboarding suite | 60 tests pass, including fresh-project capacity regressions |
| Slack reference suite | 36 tests pass |
| Local review → saved facts → meeting prep | Pass through the installed package |
| Linux ARM64 packaging | Pass |
| Five published cloud templates | cfn-lint and AWS ValidateTemplate pass |
| CLI browser login → Python helper | Real authenticated call passes; CRT installs automatically |
| AWS Agent Toolkit catalog and MCP connection | Verified separately |
| Project/model access | Free plan; Nova Lite available and authorized in the selected Region |
| Fresh AWS provisioning | All three stacks complete; Runtime, demo endpoint, Gateway and target READY |
| Deployed worker | Enabled SQS mapping caps jobs at two; shared Lambda capacity with no reservation |
| Backend call review | HTTP 202; saves stage `Proposal`, amount `24000` and renewal date `2027-02-01` through filtering and commit MCP tools |
| Separate backend meeting prep | HTTP 202; reads the same three facts from one DynamoDB event through the read MCP tool |
| Access boundary | Unsigned backend/Runtime requests rejected with 403; unsigned Gateway request rejected with 401 |
| Public attribution | Stack tags/outputs and prepared Slack manifest point to `https://deploy.rohankataria.com` |
| New Slack app | Supplied manifest generated; installation, private credentials and actual Slack UI requests not yet tested |

The retest caught two setup defects that are fixed in the public helper: a
missing AWS browser-login crypto dependency and a Lambda reservation that could
not fit a new project's 10-execution quota. The corrected template keeps the
queue's two-job limit without reserving capacity. With explicit approval, the
empty failed stack record was removed and the corrected helper retried while
preserving the successful foundation, Runtime and CRM table. No quota increase,
billing-plan upgrade or broader IAM access was needed.

The backend pair used three model calls and reported 3,212 tokens in total.
These are execution observations, not a settled bill or a throughput claim.
The retained KMS key and two Secrets Manager secrets have an estimated fixed
baseline of USD $1.80/month before usage; an overlapping audit trail can add
management-event charges. The approved $5 smoke allowance is a planning limit,
not an enforced billing cap. cfn-guard compliance checks were not performed.

The public prompts supply the commands, pinned dependencies, cloud templates,
versioned skills and Slack manifest. To finish a new Slack installation, complete
[the Slack prompt](../prompts/04-slack.md): workspace consent, private `.env`
entry, approved member grants, and actual `/gtm` commands in an approved test
channel. Backend execution, signed HTTP replay, and Slack UI delivery are
different checks. Existing Slack success does not prove a fresh installation.

The approved demo remains unchanged. An anonymous public README request loaded
the embedded MP4 successfully, and its bytes matched the approved video.
