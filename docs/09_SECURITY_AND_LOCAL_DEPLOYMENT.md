# Security and Local Deployment

## Local-first requirement

PackBridge is intended to run without cloud AI services.

Core document processing should remain on local infrastructure:

- source files stay local;
- OCR/vision, if required, is local;
- LLM inference is local through Ollama;
- canonical data is stored locally;
- SSD generation is local.

## Initial deployment model

Recommended first deployment:

- Ubuntu 24.04 server;
- Python/Flask web application;
- SQLite;
- local filesystem storage;
- Ollama on the same server or trusted LAN endpoint;
- browser access from the local network;
- PackBridge web port **5085** for the initial Ubuntu deployment.

## Configuration

Use environment variables for deployment-specific settings, including:

- Flask secret;
- database path;
- source/output storage root;
- Ollama URL;
- preferred model;
- model timeout;
- maximum upload size;
- knowledge directory;
- SSD template directory.

Do not hard-code server addresses into application logic.

## Network boundary

If Ollama is on another LAN host, support an authenticated reverse proxy or another controlled local-network access method.

Document content must not be sent to internet services by default.

## File handling

- Preserve uploaded originals.
- Sanitize filenames and use generated internal identifiers.
- Prevent path traversal.
- Do not execute uploaded files.
- Treat Office macros as data only; current SSD output does not require macros.
- Limit accepted file types and size.
- Keep generated files separated from uploads.

## Authentication and roles

POC may begin with simple local authentication, but production should consider roles such as:

- Viewer
- Processor / Editor
- Approver
- Knowledge Administrator
- System Administrator

The role model should prevent ordinary users from silently changing global Knowledge rules.

## Audit security

Audit history should be append-oriented from the application perspective.

Do not let ordinary edit actions silently rewrite prior audit entries.

## Backups

Production handover should include backup for:

- SQLite database;
- knowledge documents;
- SSD templates;
- application configuration;
- generated audit/job metadata where retention requires it.

Source and generated files may use a separate retention policy.

## Diagnostics

Provide a simple diagnostics screen for:

- application version;
- database health;
- storage health;
- Ollama reachability;
- configured model availability;
- Knowledge load status;
- active SSD template version.

Avoid exposing secrets in diagnostics or logs.
