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
