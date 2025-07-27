# TTS Batch API

[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border-orange.json)](https://github.com/copier-org/copier)
[![python](https://img.shields.io/badge/Python-3.12-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v0.json)](https://github.com/charliermarsh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

> **For developers**: Read [AGENTS.md](./AGENTS.md) for coding standards and architecture decisions

A FastAPI-based Text-to-Speech service using PIPER TTS engine with Redis caching for high-performance audio synthesis.

## Features

- 🎤 **High-quality TTS**: PIPER neural TTS engine with ONNX models
- ⚡ **Redis Caching**: Intelligent audio caching with configurable TTL
- 🔒 **Token Authentication**: Simple header-based API security
- 🐳 **Container Ready**: Kubernetes-optimized deployment
- 📦 **Auto Model Management**: Automatic voice model downloading

## Quick Start

### Using Docker

```bash
docker run -p 8000:8000 \
  -e ALLOWED_USER_TOKEN=your-secret-token \
  -e REDIS_HOST=your-redis-host \
  stkr22/tts-batch-api
```

### Local Development

```bash
# Install dependencies
uv sync --group dev

# Set environment variables
export ALLOWED_USER_TOKEN=debug-token
export REDIS_HOST=localhost

# Run the API
uv run uvicorn app.main:app --reload
```

## API Usage

```bash
# Basic usage (defaults to ryan-medium model at 16kHz)
curl -X POST "http://localhost:8000/synthesizeSpeech" \
  -H "user-token: your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is a test message"}' \
  --output audio.raw

# Advanced usage with model and sample rate selection
curl -X POST "http://localhost:8000/synthesizeSpeech" \
  -H "user-token: your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "sample_rate": 16000, "model": "ryan-medium"}' \
  --output audio.raw
```


## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `ALLOWED_USER_TOKEN` | Required | Authentication token |
| `TTS_MODEL` | `en_US-ryan-medium.onnx` | Voice model to use |
| `REDIS_HOST` | `localhost` | Redis server hostname |
| `REDIS_PORT` | `6379` | Redis server port |
| `REDIS_PASSWORD` | None | Redis authentication |
| `ENABLE_CACHE` | `true` | Enable audio caching |
| `CACHE_TTL` | `604800` | Cache TTL in seconds (7 days) |
| `ASSETS_DIR` | `/app/assets` | Voice model storage directory |

## Documentation

- 📖 **[Complete Documentation](./docs/)** - Detailed guides and API reference
- 🏗️ **[Architecture Guide](./docs/architecture.md)** - System design and components
- 🚀 **[Deployment Guide](./docs/deployment.md)** - Container and Kubernetes setup
- 🔧 **[Development Guide](./docs/development.md)** - Contributing and local setup

## License

GNU General Public License v3.0 - see [LICENSE](./LICENSE)
