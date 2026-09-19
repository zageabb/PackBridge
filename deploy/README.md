# PackBridge Ubuntu deployment

PackBridge is assigned host TCP port **5085**.

These files follow the existing Universal Deployment Agent / user-systemd pattern, but they do not modify the live server registry automatically.

## First deployment

Example checkout:

~~~bash
cd ~/ollama-chat
git clone https://github.com/zageabb/PackBridge.git
cd PackBridge
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
~~~

Create operational directories outside the Git checkout:

~~~bash
mkdir -p ~/.local/share/packbridge/data
mkdir -p ~/.local/share/packbridge/ssd_templates
mkdir -p ~/.config/packbridge
cp deploy/packbridge.env.example ~/.config/packbridge/packbridge.env
chmod 600 ~/.config/packbridge/packbridge.env
~~~

Install the user service:

~~~bash
mkdir -p ~/.config/systemd/user
cp deploy/packbridge.service ~/.config/systemd/user/packbridge.service
systemctl --user daemon-reload
systemctl --user enable --now packbridge.service
~~~

The service runs the checked-in Flask-Migrate/Alembic migrations before Gunicorn starts. Production configuration sets `PACKBRIDGE_AUTO_CREATE_DB=0`, so schema changes are owned by migrations rather than `db.create_all()`.

For a manual migration check:

~~~bash
set -a
source ~/.config/packbridge/packbridge.env
set +a
.venv/bin/python -m flask --app wsgi:application db upgrade
.venv/bin/python -m flask --app wsgi:application db current
~~~

Verify:

~~~bash
curl -fsS http://127.0.0.1:5085/health
systemctl --user status packbridge.service
~~~

Then open:

~~~text
http://192.168.1.249:5085/
~~~

## Universal Deployment Agent

`uda-registry-fragment.json` is a registry fragment, not a complete agent configuration.

Add it to the local `applications` array only after:

1. confirming port 5085 is still unused on the live host;
2. confirming the checkout is clean;
3. confirming operational data is outside the repository;
4. successfully starting the service manually;
5. confirming `/health` returns HTTP 200.

Keep `auto_deploy: false` for the first live test. Enable automatic deployment only after a successful manual deploy/update cycle.

## Local model

The example environment uses:

~~~text
http://127.0.0.1:11434
qwen3:14b
~~~

The application Settings page can override the active Ollama URL/model at runtime.

## Optional local authentication

Authentication is disabled by default for trusted development use. For production set:

~~~text
PACKBRIDGE_AUTH_ENABLED=1
PACKBRIDGE_USERS_FILE=/home/zageabb/.config/packbridge/users.json
~~~

Create the first administrator with:

~~~bash
set -a
source ~/.config/packbridge/packbridge.env
set +a
.venv/bin/python -m flask --app wsgi:application packbridge init-user --username admin --role admin
~~~

Do not copy plaintext passwords into Git or the environment file.

## Optional scanned-PDF OCR

PackBridge prefers digital text extraction. To enable the fully local fallback for scanned PDFs, install Tesseract on the host and set:

~~~text
PACKBRIDGE_OCR_MODE=tesseract
PACKBRIDGE_OCR_LANGUAGE=eng
~~~

If Tesseract is not installed, keep OCR mode off. `/ready` reports whether the executable is available.

## Backup, retention and logs

Operational backup/log paths are external to the Git checkout.

Example manual backup:

~~~bash
.venv/bin/python -m flask --app wsgi:application packbridge backup
~~~

Install the optional timers:

~~~bash
cp deploy/packbridge-backup.service deploy/packbridge-backup.timer ~/.config/systemd/user/
cp deploy/packbridge-retention.service deploy/packbridge-retention.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now packbridge-backup.timer packbridge-retention.timer
~~~

Retention deletion is disabled by default (PACKBRIDGE_RETENTION_DAYS=0 and PACKBRIDGE_BACKUP_RETENTION_DAYS=0). Set non-zero periods only after the production retention policy is agreed.

## Model qualification

Run the same controlled golden set against both local candidates:

~~~bash
.venv/bin/python -m flask --app wsgi:application packbridge benchmark --model qwen3:14b
.venv/bin/python -m flask --app wsgi:application packbridge benchmark --model qwen3:8b
~~~

Then compare the generated JSON reports with `packbridge benchmark-compare`.

## SAP production release gates

Production generation is deliberately locked by default. These flags represent external business/SAP acceptance, not development switches:

~~~text
PACKBRIDGE_SAP_OUTPUT_APPROVED=0
PACKBRIDGE_SAP_SOCS_ONLY_APPROVED=0
PACKBRIDGE_SAP_MACRO_FREE_APPROVED=0
~~~

Leave them disabled until the acceptance steps in `docs/17_ACCEPTANCE_AND_BENCHMARK.md` are complete.

The full production handover and recovery procedure is in `docs/18_PRODUCTION_HANDOVER.md`.
