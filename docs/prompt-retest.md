# Prompt reproduction test

Tested in a separate Codex chat from a fresh public clone, without private source
or deployment artifacts. The clean environment at `e5f1a17` reproduced the local
setup and authenticated AWS helper calls.

| Check | Observed result |
|---|---|
| Supplied bootstrap | Pass; creates the environment and installs all AWS dependencies |
| Portable/onboarding suite | 58 tests pass |
| Slack reference suite | 36 tests pass |
| Local review → saved facts → meeting prep | Pass through the installed package |
| Linux ARM64 packaging | Pass |
| Four reference templates | Local lint and AWS template validation pass |
| CLI browser login → Python helper | Pass after the published CRT dependency fix |
| AWS Agent Toolkit catalog and MCP connection | Verified separately |
| Existing project and service access | Free plan; Runtime/Gateway reads pass; Nova Lite available and authorized in the selected Region |
| Fresh AWS provisioning | Not run; requires approval of the dedicated resource/cost plan |
| New Slack app installation and live requests | Not run in the fresh clone; requires workspace consent and private settings |

The first retest caught a missing `botocore[crt]` dependency. The repository now
installs it automatically; a second pristine environment verified the fix with
real authenticated helper calls. The review also caught an incorrect advertised
token limit. The supplied plan now matches the reference: call review uses up to
three calls at 640 output tokens each; meeting prep uses one at 500.

The public prompts supply the commands, cloud templates, pinned dependencies,
versioned catalog and Slack manifest. A full new cloud/Slack installation remains
an explicit next test. Existing deployment evidence, HTTP replay and Slack UI
installation are different checks; the helpers report them separately.
