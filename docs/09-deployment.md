# 09 — Deployment Guide

Step-by-step instructions to deploy the chatbot backend on a Linux server (Ubuntu 22.04 / Debian 12 recommended).

---

## Hardware Requirements

| Tier | Use case | CPU | RAM | Disk | Network |
|---|---|---|---|---|---|
| **Minimum** | Dev / low traffic (< 50 req/day) | 2 vCPU | 2 GB | 20 GB SSD | 100 Mbps |
| **Recommended** | Production (< 500 req/day) | 4 vCPU | 4 GB | 40 GB SSD | 1 Gbps |
| **High traffic** | > 500 req/day or large doc library | 8 vCPU | 8 GB | 80 GB SSD | 1 Gbps |

> **Note on RAM**: The sentence-transformers embedding model (`all-MiniLM-L6-v2`) loads ~90 MB into memory at startup. ChromaDB keeps its index in memory proportional to the number of embedded chunks. 4 GB RAM is comfortable for most deployments.

> **GPU**: Not required. All embedding and inference are done via external API providers. Only Ollama (local models) benefits from a GPU.

---

## Software Requirements

| Software | Minimum version | Purpose |
|---|---|---|
| Python | 3.10+ | Runtime |
| pip | 23+ | Package installer |
| MySQL | 8.0+ | Primary database |
| nginx | 1.18+ | Reverse proxy / TLS termination |
| certbot | any | Free SSL certificate (Let's Encrypt) |
| systemd | any | Process management |
| git | any | Deploying code |

---

## 1. Server Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx curl

# Install MySQL server
sudo apt install -y mysql-server

# Verify Python version (must be 3.10+)
python3 --version
```

---

## 2. Create a Dedicated User

Run the app as a non-root user for security.

```bash
sudo useradd -m -s /bin/bash chatbot
sudo su - chatbot
```

All remaining steps run as the `chatbot` user unless noted.

---

## 3. Clone the Repository

```bash
cd /home/chatbot
git clone <your-repo-url> app
cd app
```

---

## 4. Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate

# Install all dependencies
pip install --upgrade pip
pip install -e .
```

This installs everything listed in `pyproject.toml`: FastAPI, Uvicorn, ChromaDB, sentence-transformers, all AI provider SDKs, SQLAlchemy, Alembic, `aiomysql`, and auth libraries.

---

## 5. MySQL Database Setup

### Secure MySQL installation

```bash
sudo mysql_secure_installation
# Follow prompts: set root password, remove test DB, disallow remote root login
```

### Create database and user

```bash
sudo mysql -u root -p
```

Run these SQL commands inside the MySQL prompt:

```sql
CREATE DATABASE chatbot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'chatbot'@'localhost' IDENTIFIED BY 'yourpassword';
GRANT ALL PRIVILEGES ON chatbot.* TO 'chatbot'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

> Use a strong unique password for `chatbot` user. Replace `yourpassword` everywhere.

### Verify connection

```bash
mysql -u chatbot -p chatbot
# Should open a MySQL prompt without error
EXIT;
```

---

## 6. Storage Directories

```bash
mkdir -p storage/files storage/chroma_db logs
```

---

## 6. Environment Configuration

Copy the example and fill in your values:

```bash
cp .env.example .env
nano .env
```

### Required values to set

**AI Provider keys** — add at least one:
```env
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
GEMINI_API_KEY=AIza-xxx
# ... add whichever providers you use
```

**Default provider** — must match a provider you have a key for:
```env
DEFAULT_PROVIDER=anthropic
DEFAULT_MODEL=claude-haiku-4-5-20251001
```

**Secret keys** — generate fresh random values:
```bash
# Generate AUTH_SECRET_KEY (64-char hex)
python3 -c "import secrets; print(secrets.token_hex(32))"

# Generate CSRF_SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"

# Generate ADMIN_TOTP_ENCRYPTION_KEY (Fernet key)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Set the generated values in `.env`:
```env
AUTH_SECRET_KEY=<64-char hex from above>
CSRF_SECRET_KEY=<another 64-char hex>
ADMIN_TOTP_ENCRYPTION_KEY=<Fernet key>
```

**Database** — use the MySQL user and database created in step 5:
```env
HISTORY_DB_URL=mysql+aiomysql://chatbot:yourpassword@localhost:3306/chatbot
```

**Storage paths** — use absolute paths in production:
```env
STORAGE_ROOT=/home/chatbot/app/storage/files
CHROMA_PATH=/home/chatbot/app/storage/chroma_db
META_DB_PATH=/home/chatbot/app/storage/meta.json
```

**API settings**:
```env
API_HOST=127.0.0.1
API_PORT=8000
LOG_LEVEL=INFO
```

> Set `API_HOST=127.0.0.1` (not `0.0.0.0`) — nginx will proxy to it; you don't want the app directly exposed.

---

## 7. Create the Master Admin Account

```bash
source .venv/bin/activate
python3 scripts/create_admin.py
```

Follow the prompts — enter a username and strong password. The script bcrypt-hashes the password and writes `MASTER_ADMIN_USERNAME` and `MASTER_ADMIN_PASSWORD_HASH` to `.env` automatically.

---

## 8. Database Migration

```bash
source .venv/bin/activate
alembic upgrade head
```

This creates all tables in `storage/app.db`. Run this again after every code update.

---

## 9. Test the Server (Before Daemonising)

```bash
source .venv/bin/activate
uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Visit `http://<server-ip>:8000/health` — you should get `{"status": "ok"}`.

Press `Ctrl+C` to stop, then continue to the next step.

---

## 10. systemd Service

Create the service file as root:

```bash
sudo nano /etc/systemd/system/chatbot.service
```

Paste:

```ini
[Unit]
Description=MageComp Chatbot API
After=network.target

[Service]
Type=exec
User=chatbot
Group=chatbot
WorkingDirectory=/home/chatbot/app
Environment="PATH=/home/chatbot/app/.venv/bin"
EnvironmentFile=/home/chatbot/app/.env
ExecStart=/home/chatbot/app/.venv/bin/uvicorn src.api.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 2 \
    --log-level info \
    --access-log \
    --log-config /home/chatbot/app/src/log_config.json
Restart=on-failure
RestartSec=5
StandardOutput=append:/home/chatbot/app/logs/app.log
StandardError=append:/home/chatbot/app/logs/error.log

[Install]
WantedBy=multi-user.target
```

> **Workers**: Set `--workers` to `(2 × CPU cores) + 1`. For 2 vCPU use `--workers 2`, for 4 vCPU use `--workers 4`. Do not exceed available RAM.

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable chatbot
sudo systemctl start chatbot

# Verify it's running
sudo systemctl status chatbot
```

---

## 11. Nginx Reverse Proxy

```bash
sudo nano /etc/nginx/sites-available/chatbot
```

Paste (replace `chat.yourdomain.com`):

```nginx
server {
    listen 80;
    server_name chat.yourdomain.com;

    # Redirect all HTTP to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name chat.yourdomain.com;

    # SSL — filled in by certbot
    ssl_certificate     /etc/letsencrypt/live/chat.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chat.yourdomain.com/privkey.pem;
    include             /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam         /etc/letsencrypt/ssl-dhparams.pem;

    # Proxy all requests to uvicorn — FastAPI serves /widget/ and /static/ itself
    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        # Required for SSE streaming responses
        proxy_set_header   Connection        '';
        proxy_buffering    off;
        proxy_cache        off;
        chunked_transfer_encoding on;

        # Timeouts — increase for long LLM responses
        proxy_read_timeout  120s;
        proxy_send_timeout  120s;
    }

    # Upload size limit — increase if you upload large documents
    client_max_body_size 50M;
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 12. SSL Certificate

```bash
sudo certbot --nginx -d chat.yourdomain.com
```

Follow the prompts. Certbot will auto-configure the SSL block and set up auto-renewal.

Test auto-renewal:
```bash
sudo certbot renew --dry-run
```

---

## 13. Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

Port 8000 (uvicorn) must NOT be open — it is only accessible via nginx on localhost.

---

## 14. Verify the Deployment

```bash
# Health check
curl https://chat.yourdomain.com/health

# Admin portal
# Open in browser: https://chat.yourdomain.com/admin/

# Tail logs
tail -f /home/chatbot/app/logs/app.log
```

---

## 15. Embed the Widget on Your Site

Once deployed, add this to any HTML page:

```html
<script
  src="https://chat.yourdomain.com/widget/magecomp-chat.js"
  data-app-id="your-app-id"
  data-api-url="https://chat.yourdomain.com"
></script>
```

See [01-quick-start.md](01-quick-start.md) for full widget configuration options.

---

## Updating the App

```bash
cd /home/chatbot/app
git pull

source .venv/bin/activate
pip install -e .               # install any new dependencies
alembic upgrade head           # apply any new DB migrations

sudo systemctl restart chatbot
```

---

## Log Rotation

Prevent log files from growing unbounded:

```bash
sudo nano /etc/logrotate.d/chatbot
```

```
/home/chatbot/app/logs/*.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
    copytruncate
}
```

---

## Troubleshooting

| Symptom | Check |
|---|---|
| `502 Bad Gateway` | `sudo systemctl status chatbot` — is uvicorn running? |
| `500` on chat | `tail -f logs/error.log` — usually a missing API key or bad `.env` |
| Streaming (SSE) cuts off | Confirm `proxy_buffering off` in nginx config |
| Widget JS returns 404 | Restart uvicorn — FastAPI mounts `/widget/` on startup |
| `Can't connect to MySQL` | Check `HISTORY_DB_URL` in `.env`; verify MySQL is running: `sudo systemctl status mysql` |
| `Access denied for user` | Re-run the `GRANT` SQL in step 5 with correct username/password |
| `Table doesn't exist` | Run `alembic upgrade head` — migrations not applied yet |
| Admin login fails | Re-run `python3 scripts/create_admin.py` to reset password |
| ChromaDB OOM on startup | Reduce `EMBED_BATCH_SIZE` in `.env` or increase server RAM |

---

## Production Checklist

- [ ] `.env` file has no placeholder values (`xxx`, `replace-with-...`)
- [ ] `HISTORY_DB_URL` points to MySQL with real credentials (not the example password)
- [ ] MySQL `chatbot` database and user created; `GRANT` applied
- [ ] `alembic upgrade head` run — all tables created
- [ ] `AUTH_SECRET_KEY`, `CSRF_SECRET_KEY`, `ADMIN_TOTP_ENCRYPTION_KEY` are unique random values
- [ ] `API_HOST=127.0.0.1` (not `0.0.0.0`)
- [ ] SSL certificate installed and auto-renewal working
- [ ] Firewall enabled — only ports 22, 80, 443 open; port 3306 not exposed externally
- [ ] Port 8000 not reachable from the internet
- [ ] `MASTER_ADMIN_PASSWORD_HASH` set (not plaintext)
- [ ] `storage/` directory has correct permissions (`chown -R chatbot:chatbot storage/`)
- [ ] Log rotation configured
