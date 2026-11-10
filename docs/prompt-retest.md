# Prompt reproduction test

The prompts are being tested in a separate Codex chat using a fresh public clone.
The tester gets only the public repository and its prompts, rather than the
private working source or deployment artifacts.

The baseline found missing AWS Toolkit setup, cloud templates, Runtime dependency
packaging, a pinned catalog deployment and a Slack app manifest. Those gaps are
now supplied by the numbered prompts and `scripts/pipeline_*.py` helpers.
The local bootstrap also prepares Python before running the setup checker and
uses a wheel install to avoid the baseline’s macOS editable `.pth` import issue.

Revised prompt retest results will be recorded here after the separate run.
Local/offline tests, authentication, fresh AWS provisioning, signed HTTP replay,
and an actual command sent from Slack are reported separately. Existing live
deployment evidence is not a fresh-clone or fresh-installation pass.
