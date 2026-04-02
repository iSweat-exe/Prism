# Prism

A system monitoring and management API built with FastAPI. Prism exposes real-time metrics for CPU, RAM, disk, network, and processes, along with Docker container management and PM2 process control. (More modules coming soon.)

## Architecture

The API runs directly on the host via PM2, giving it native access to all system resources. Nginx runs in Docker and proxies requests to the host API.

```
Internet → Nginx (Docker :80) → host.docker.internal:8081 → Prism API (PM2)
```

> [!TIP]
> This design follows the same approach used by Prometheus `node_exporter`, Netdata, and Glances monitoring agents belong on the host, not inside containers.

## Requirements

- Python 3.14+
- Node.js (for PM2) - (Optional)
- Docker & Docker Compose (for Nginx gateway) - (Optional)

## Installation

**1. Clone the repository**
```bash
git clone https://github.com/iSweat-exe/Prism.git
cd Prism
```

**2. Create a virtual environment and install dependencies**
```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

**3. Install PM2 - (optional)**
```bash
npm install -g pm2
```

**4. Start the API**
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup   # follow the printed command to enable autostart on reboot
```

**5. Start the Nginx gateway**
```bash
docker compose up -d
```

The API is now reachable at `http://localhost`. Interactive documentation is available at `http://localhost/docs`.

## Development

```bash
python main.py   # run locally on http://127.0.0.1:8081
ruff check .     # lint
pytest           # tests
```

## Logs

PM2 logs are written to `/var/log/prism/`.

```bash
pm2 logs prism-api
```

## Security

The API has no built-in authentication and is intended for local network use only. Configure CORS origins in `main.py` before any public exposure.

## License

MIT License © 2026 iSweat