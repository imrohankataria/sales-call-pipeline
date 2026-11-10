# Prompt reproduction test

Tested in a separate Codex chat from a fresh public clone, without private source
or deployment artifacts. The clean environment reproduced local setup and
authenticated AWS helper calls. The subsequently approved fresh AWS run found
a Lambda capacity incompatibility that the public deployment helper now fixes.

| Check | Observed result |
|---|---|
| Supplied bootstrap | Pass; creates the environment and installs all AWS dependencies |
| Portable/onboarding suite | 60 tests pass, including the fresh-project concurrency regression |
| Slack reference suite | 36 tests pass |
| Local review → saved facts → meeting prep | Pass through the installed package |
| Linux ARM64 packaging | Pass |
| Four reference templates | Local lint and AWS template validation pass |
| CLI browser login → Python helper | Pass after the published CRT dependency fix |
| AWS Agent Toolkit catalog and MCP connection | Verified separately |
| Existing project and service access | Free plan; Runtime/Gateway reads pass; Nova Lite available and authorized in the selected Region |
| Fresh AWS provisioning | Foundation and Runtime created; Slack/Gateway rolled back because a two-execution reservation cannot fit a 10-execution Lambda quota. Corrected template passes local lint and AWS validation; fresh recovery still pending |
| New Slack app installation and live requests | Not run in the fresh clone; requires workspace consent and private settings |

The first retest caught a missing `botocore[crt]` dependency. The repository now
installs it automatically; a second pristine environment verified the fix with
real authenticated helper calls. The review also caught an incorrect advertised
token limit. The supplied plan now matches the reference: call review uses up to
three calls at 640 output tokens each; meeting prep uses one at 500.

The fresh cloud run exposed another portability issue: reserving two Lambda
executions leaves fewer than the project's required 10 unreserved executions.
The corrected template keeps the SQS limit of two simultaneous worker jobs
without reserving shared capacity. The helper checks capacity before stack/state
changes. The regression tests reproduce both the original quota constraint and
an insufficient-capacity failure. No quota increase or plan upgrade is needed.
CloudFormation rolled back all 23 resources in the failed Slack stack; the
successful foundation and Runtime are preserved. An empty `ROLLBACK_COMPLETE`
stack needs explicit recovery approval before removal and retry.

The public prompts supply the commands, cloud templates, pinned dependencies,
versioned catalog and Slack manifest. The fresh cloud retry and new Slack
installation remain unfinished tests. Existing deployment evidence, HTTP replay and Slack UI
installation are different checks; the helpers report them separately.
