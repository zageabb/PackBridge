# External Acceptance Checklist

PackBridge software development is complete for the currently verified scope. The items in this document require the live Ubuntu host, the real business/SAP process, or production-owner decisions and therefore cannot be completed safely from source code alone.

## 1. First live deployment

- Recheck port 5085 on the Ubuntu host.
- Clone/update `/home/zageabb/ollama-chat/PackBridge`.
- Create the production virtual environment and install requirements.
- Run `flask --app wsgi:application db upgrade`.
- Start `packbridge.service` manually.
- Verify `/health` returns HTTP 200 and `/ready` reports Ollama reachable.
- Verify the Application Home link opens PackBridge on port 5085.
- Keep the Universal Deployment Agent entry monitor-only for the first cycle.
- After a successful manual update/restart/health cycle, decide whether to set `auto_deploy` true in the live UDA registry.

## 2. Controlled SSD template acceptance

- Install the approved reference SSD workbook through Settings.
- Derive/activate the clean generation template.
- Record the template SHA-256 and structural fingerprint.
- Confirm that the clean template is the workbook version approved by the business process owner.

## 3. Real packing-list regression

- Process the supplied HE reference packing list with `qwen3:14b`.
- Confirm 20 source pages collapse to the expected 17 cases.
- Review line items, dimensions, weights and UOMs against source evidence.
- Build a validation SSD and compare the position-10 SoCs rows with the approved working data.
- Add further real vendor examples to the golden set only when safe to retain and manually approved.

## 4. SAP import acceptance

PackBridge intentionally cannot self-certify SAP compatibility.

Run an actual SAP acceptance import using a structurally verified PackBridge validation workbook and record:

- PackBridge commit;
- model/version;
- active Knowledge profile/version and SHA-256;
- template SHA-256;
- output SHA-256;
- structural fingerprint;
- SAP environment/test reference;
- acceptance result and approver.

If the SAP path accepts the deterministic SoCs dataset without requiring PackBridge to recreate generated PL/ML sheets, set:

    PACKBRIDGE_SAP_OUTPUT_APPROVED=1
    PACKBRIDGE_SAP_SOCS_ONLY_APPROVED=1

After service restart, the production Generate SSD action becomes available for clean, warning-free projects to authorised approvers/admins.

If SAP requires PackBridge-created PL/ML item sheets rather than the existing workbook/VBA workflow, do **not** enable `PACKBRIDGE_SAP_SOCS_ONLY_APPROVED`. Capture a verified workbook/example that establishes the required physical PL/ML cell mappings; that evidence becomes a new development scope rather than guessing the layout.

## 5. Macro-free XLSX acceptance

Macro-free output is implemented as a release-gated path but remains disabled by default.

Only after SAP accepts a clean XLSX template/output should the production owner set:

    PACKBRIDGE_SAP_MACRO_FREE_APPROVED=1

Until then, continue using the macro-enabled controlled template.

## 6. Model qualification on the real host

Run:

    flask --app wsgi:application packbridge benchmark --model qwen3:14b
    flask --app wsgi:application packbridge benchmark --model qwen3:8b

Then compare the generated reports:

    flask --app wsgi:application packbridge benchmark-compare BASELINE.json CANDIDATE.json

Record host RAM/VRAM use and latency alongside the generated accuracy metrics. Keep `qwen3:14b` unless the smaller candidate passes the quality gates in `docs/17_ACCEPTANCE_AND_BENCHMARK.md` and provides a meaningful resource/latency benefit.

## 7. Production-owner policy decisions

- Decide whether authentication should be enabled in the trusted LAN deployment. The role system is implemented either way.
- If authentication is enabled, create named accounts and assign least-privilege roles.
- Agree operational-file and backup retention periods. Automatic deletion remains disabled while the configured periods are 0.
- Confirm backup destination/copy policy and perform a restore drill.
- Decide when/if the live UDA entry should move from monitor-only to auto-deploy.

## Completion definition

Source development is complete when CI passes and this checklist is the only remaining work. Production acceptance is complete only when the applicable external checks above have been performed and the corresponding release gates are explicitly enabled.
