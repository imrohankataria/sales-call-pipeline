# Prompt reproduction test

Tested in a separate Codex chat from a fresh public clone, without the original
private source or deployment artifacts. The supplied AWS helper at `96e771e`
completed a dedicated deployment and a real backend save-and-read workflow.
The resources were kept as requested. Slack UI verification reused the user's
existing GTM app, as requested; a second app was not installed.

| Check | Observed result |
|---|---|
| Supplied bootstrap | Pass; Python 3.12 and AWS dependencies installed |
| Portable/onboarding suite | 61 tests pass, including fresh-project capacity and Slack manifest regressions |
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
| Existing Slack app | Actual `/gtm skills` private directory and one call-review/meeting-prep pair passed; both completed replies contain the implementation-help link |
| Independent existing-app AWS check | Both jobs completed with Slack delivery receipts; call review saved exactly one CRM event, meeting prep read it, and service logs confirmed the three expected MCP tool calls with matching actor identity |
| New Slack manifest | Corrected manifest passes Slack's UI validation with only `commands` and `chat:write`; no second app created or installed |

The retest caught two setup defects that are fixed in the public helper: a
missing AWS browser-login crypto dependency and a Lambda reservation that could
not fit a new project's 10-execution quota. The corrected template keeps the
queue's two-job limit without reserving capacity. With explicit approval, the
empty failed stack record was removed and the corrected helper retried while
preserving the successful foundation, Runtime and CRM table. No quota increase,
billing-plan upgrade or broader IAM access was needed.

Slack's app-creation screen caught another onboarding defect: the supplied long
description was shorter than App Settings' 174-character minimum. The helper now
generates a valid description, a regression checks the documented limits, and
the corrected manifest reached Slack's reviewed-settings screen without errors.
The draft was canceled after validation. Existing app settings were not changed.

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
channel. This retest used the existing app's deployed route for Slack and the
dedicated new deployment for the fresh AWS/backend pair. These are separate
checks; existing Slack success does not prove fresh OAuth installation. No
second human member was available for a denied-access UI test; the offline and
signed-fixture authorization checks cover that boundary separately.

The approved demo remains unchanged. An anonymous public README request loaded
the embedded MP4 successfully, and its bytes matched the approved video.
