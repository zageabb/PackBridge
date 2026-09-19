# PackBridge Production Handover Guide

## Deployment identity

- Application: PackBridge
- Repository: zageabb/PackBridge
- Host port: 5085
- Default local mapper: qwen3:14b
- Runtime: Flask/Gunicorn with SQLite and local Ollama
- Deployment pattern: user systemd plus Universal Deployment Agent

## First installation

1. Clone the repository to /home/zageabb/ollama-chat/PackBridge.
2. Create .venv and install requirements.txt.
3. Copy deploy/packbridge.env.example to ~/.config/packbridge/packbridge.env.
4. Keep operational data, backups, logs, user accounts and templates outside the Git checkout.
5. Copy deploy/packbridge.service to ~/.config/systemd/user/.
6. Run the migration command once and verify it succeeds.
7. Start the service manually and verify http://127.0.0.1:5085/health.
8. Only after the manual health check should the UDA entry be enabled for automatic deployment.

## Optional scanned-document OCR

Digital PDFs are preferred. To enable the local scanned-PDF fallback, install Tesseract on the host and set:

    PACKBRIDGE_OCR_MODE=tesseract
    PACKBRIDGE_OCR_LANGUAGE=eng

OCR runs on the local host. It is not sent to a cloud OCR service.

## Authentication and roles

Authentication is optional for trusted development environments and is disabled by default.

For production:

    PACKBRIDGE_AUTH_ENABLED=1
    PACKBRIDGE_USERS_FILE=~/.config/packbridge/users.json

Create users without putting plaintext passwords in source control:

    flask --app wsgi:application packbridge init-user --username admin --role admin

Available roles:

- viewer — read-only access;
- processor — upload, map, edit, chat and project preparation;
- approver — processor permissions plus validation acknowledgement and output generation;
- knowledge_admin — processor permissions plus Knowledge approval/rejection;
- admin — all capabilities including Settings/template administration.

The role policy is enforced centrally on HTTP routes. Passwords are stored only as Werkzeug password hashes in the external users file.

## Logs

Application logs are written to PACKBRIDGE_LOG_ROOT/packbridge.log with rotation. Default rotation is 5 MB with five retained files. Gunicorn/systemd logs remain available through journalctl.

Useful checks:

    journalctl --user -u packbridge.service
    tail -f ~/.local/state/packbridge/packbridge.log

## Backup and restore

Create an on-demand backup:

    flask --app wsgi:application packbridge backup

The backup contains the SQLite database, operational data, Knowledge documents and controlled SSD templates. It deliberately excludes secrets and environment files.

Inspect before restore:

    flask --app wsgi:application packbridge backup-inspect /path/to/backup.zip

Restore only while the PackBridge web service is stopped:

    systemctl --user stop packbridge.service
    flask --app wsgi:application packbridge restore /path/to/backup.zip --yes
    systemctl --user start packbridge.service

Daily backup and weekly retention systemd timer examples are provided under deploy/.

## Retention

Default operational-file retention is 90 days and backup retention is 30 days. Database audit history is not deleted by the file-retention command.

Preview cleanup:

    flask --app wsgi:application packbridge retention
    flask --app wsgi:application packbridge backup-prune

Apply cleanup:

    flask --app wsgi:application packbridge retention --apply
    flask --app wsgi:application packbridge backup-prune --apply

## Knowledge support workflow

Vendor/document behaviour lives in Markdown Knowledge files. Support changes should use the PackBridge Learning/Knowledge proposal flow:

1. reproduce the failing document;
2. correct the working data;
3. optionally propose profile learning from the corrected field;
4. review the diff;
5. approve the proposal with a Knowledge Administrator;
6. reprocess the affected document;
7. retain the audit trail and incremented profile version.

Knowledge documents can also be downloaded, updated remotely and imported back as a review-only proposal.

## Model benchmark

Run the baseline and candidate on the same golden set:

    flask --app wsgi:application packbridge benchmark --model qwen3:14b
    flask --app wsgi:application packbridge benchmark --model qwen3:8b

Then compare the two generated reports:

    flask --app wsgi:application packbridge benchmark-compare BASELINE.json CANDIDATE.json

Acceptance thresholds are documented in docs/17_ACCEPTANCE_AND_BENCHMARK.md.

## SSD template and SAP release

The controlled template must pass structural inspection and be cleaned to generation-ready state before any workbook can be built.

Validation workbooks may be generated for controlled testing. Production generation is separately release-gated by deployment configuration:

    PACKBRIDGE_SAP_OUTPUT_APPROVED=0
    PACKBRIDGE_SAP_SOCS_ONLY_APPROVED=0
    PACKBRIDGE_SAP_MACRO_FREE_APPROVED=0

Do not change these flags to 1 merely because PackBridge generated a structurally valid workbook. They represent external SAP/business acceptance decisions.

`PACKBRIDGE_SAP_OUTPUT_APPROVED` records successful production-path SAP acceptance.

`PACKBRIDGE_SAP_SOCS_ONLY_APPROVED` records confirmation that the deterministic SoCs output is sufficient for the SAP import and that PackBridge does not need to recreate PL/ML worksheets for that import.

`PACKBRIDGE_SAP_MACRO_FREE_APPROVED` records successful acceptance of macro-free XLSX output. Until then, retain the macro-enabled controlled template.

Every output record stores the file SHA-256, template SHA-256, structural fingerprint, rows/cells written and output status.

## Deployment Agent

PackBridge is included in the Universal Deployment Agent example registry as a monitor-only application on port 5085. Keep auto_deploy false for the first live deployment. Enable it only after the server checkout is clean, operational paths are external, the migration succeeds, and /health returns HTTP 200.

## Recovery checklist

1. Stop PackBridge if database/files may be inconsistent.
2. Inspect the latest backup before restoring.
3. Restore operational files and database.
4. Run flask db upgrade.
5. Start PackBridge.
6. Check /health and /ready.
7. Verify Ollama model availability in Settings.
8. Verify the active Knowledge profile and SSD template.
9. Run a known regression packing list before resuming production use.
