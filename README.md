# Prism

A lightweight, real-time system monitoring and infrastructure management API built with **FastAPI**.
Prism exposes live metrics for CPU, RAM, disk, network, and processes, along with full Docker container/image management and PM2 process control, all through a clean REST interface with SSE streaming support.

## Architecture

Prism runs directly on the host via PM2, giving it native access to all system resources. An optional Nginx container acts as a reverse-proxy gateway.

```
Internet → Nginx (Docker :80) → host.docker.internal:8081 → Prism API (PM2)
```

> [!TIP]
> This design follows the same approach used by Prometheus `node_exporter`, Netdata, and Glances: monitoring agents belong on the host, not inside containers.

## Features

### System Monitoring
- **CPU** per-core usage, frequency, brand/vendor metadata, temperatures, and real-time SSE streaming
- **RAM** virtual & swap memory stats, top 10 processes by memory consumption
- **Disk** per-partition usage, filesystem type, I/O read/write counters
- **Network** per-interface throughput (bytes, packets, errors), IP/MAC addresses, latency measurement
- **OS** hostname, kernel version, architecture, load average
- **Uptime** system boot time and formatted uptime

### Docker Management
- **Containers** list, inspect, create, start, stop, restart, delete, view logs, and live stats
- **Images** list, inspect, pull (with streamed progress), delete, and prune unused images

### PM2 Process Control
- **Processes** list all PM2-managed processes with status and performance metrics
- **Lifecycle** start, stop, restart, reload, and delete processes
- **Logs** fetch recent log lines or stream real-time logs via SSE
- **Config** save the current PM2 process list

### Core
- **Background Sampler** dedicated threads continuously sample CPU, disk, network, latency, and top processes so every API call returns instantly from cache
- **SSE Streaming** CPU, RAM, disk, and network endpoints expose `/stream` routes for live data via Server-Sent Events
- **Structured Error Handling** custom exception hierarchy with consistent JSON error responses
- **Rotating Logs** file + stdout logging with automatic 10 MB rotation (5 backups)
- **CORS** fully configurable cross-origin middleware
- **Pydantic Settings** environment-driven configuration with `.env` file support

> [!NOTE]
> Full interactive API documentation is auto-generated and available at `/docs` when the server is running.

## Requirements

- Python 3.14+
- Node.js (for PM2) *(optional)*
- Docker & Docker Compose (for Nginx gateway) *(optional)*

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

**3. Install PM2** *(optional)*
```bash
npm install -g pm2
```

**4. Start the API**
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup   # follow the printed command to enable autostart on reboot
```

**5. Start the Nginx gateway** *(optional)*
```bash
docker compose up -d
```

The API is now reachable at `http://localhost`. Interactive documentation is available at `http://localhost/docs`.

## Configuration

Prism uses Pydantic Settings, so every option can be set via environment variable or a `.env` file at the project root.

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `PrismAPI` | Application display name |
| `VERSION` | `1.0.0` | Reported API version |
| `DEBUG` | `false` | Debug mode |
| `PROCFS_PATH` | `/proc` | Path to procfs (Linux) |
| `GATEWAY_NAME` | `nginx-proxy` | Nginx container name |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FILE` | `prism.log` | Log file path |

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

## CI

A GitHub Actions pipeline runs on every push to `dev` and on pull requests targeting `master`. It installs dependencies and runs `ruff check .`.

## Security

The API has no built-in authentication and is intended for local network use only. Configure CORS origins in `app/core/middleware.py` before any public exposure.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch conventions, commit style, and workflow.

## License

MIT License © 2026 iSweat