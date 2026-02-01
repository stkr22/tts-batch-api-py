# Development Guide

This guide covers local development setup, contribution guidelines, and development workflows for the TTS Batch API.

## Prerequisites

- **Python 3.12+** (required)
- **UV** (modern Python package manager)
- **Valkey** (for local caching)
- **Git** (for version control)

## Local Development Setup

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/stkr22/tts-batch-api-py.git
cd tts-batch-api-py

# Install dependencies (automatically creates virtual environment)
uv sync --group dev

# Activate virtual environment (if needed)
source .venv/bin/activate
```

### 2. Environment Configuration

Create a `.env` file for local development:

```bash
# .env
ALLOWED_USER_TOKEN=debug-token
TTS_MODEL=en_US-kathleen-low.onnx
VALKEY_HOST=localhost
VALKEY_PORT=6379
ENABLE_CACHE=true
LOG_LEVEL=DEBUG
ASSETS_DIR=./assets
```

### 3. Start Valkey (Development)

```bash
# Using Docker
docker run -d --name dev-valkey -p 6379:6379 valkey/valkey:8-alpine

# Or using local Valkey installation
valkey-server --port 6379
```

### 4. Run the API

```bash
# Development server with auto-reload
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production-like server
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Health**: http://localhost:8000/health
- **Docs**: http://localhost:8000/docs (FastAPI auto-generated)

## Development Workflow

### Code Standards

**Read [AGENTS.md](../AGENTS.md) first** - it contains essential coding standards and architecture decisions.

**Key Points**:
- Python 3.12+ with type hints
- Google-style docstrings
- Ruff for formatting and linting
- mypy for type checking
- 120-character line limit

### Essential Commands

```bash
# Install/update dependencies
uv sync --group dev

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=app --cov-report=html

# Lint code
uv run ruff check .

# Format code
uv run ruff format .

# Type check
uv run mypy app/

# Run all pre-commit hooks
pre-commit run --all-files
```

### Git Workflow

1. **Create Feature Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**:
   - Follow coding standards in AGENTS.md
   - Add tests for new functionality
   - Update documentation as needed

3. **Run Quality Checks**:
   ```bash
   # Format and lint
   uv run ruff format .
   uv run ruff check .

   # Type check
   uv run mypy app/

   # Test
   uv run pytest
   ```

4. **Commit Changes**:
   ```bash
   # Use conventional commits with gitmoji
   git commit -m "feat: ✨ add multi-voice support [AI]"
   ```

5. **Push and Create PR**:
   ```bash
   git push origin feature/your-feature-name
   # Create PR via GitHub web interface
   ```

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=app --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_synthesize_speech.py

# Run with parallel execution
uv run pytest -n auto
```

### Test Structure

Tests are located in the `tests/` directory:

```
tests/
├── __init__.py
├── test_synthesize_speech.py  # API endpoint tests
└── conftest.py               # Shared test fixtures (future)
```

### Writing Tests

Example test structure:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_synthesize_speech_success():
    """Test successful speech synthesis."""
    with TestClient(app) as client:
        response = client.post(
            "/synthesizeSpeech",
            headers={"user-token": "DEBUG"},
            json={"text": "Hello world"}
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/x-raw"
        assert len(response.content) > 0

def test_synthesize_speech_auth_failure():
    """Test authentication failure."""
    with TestClient(app) as client:
        response = client.post(
            "/synthesizeSpeech",
            headers={"user-token": "invalid"},
            json={"text": "Hello world"}
        )
        assert response.status_code == 403
```

## Architecture Development

### Adding New Features

1. **Read Architecture Docs**: Review [architecture.md](./architecture.md)
2. **Plan Changes**: Consider impact on caching, authentication, performance
3. **Update Documentation**: Modify relevant docs and AGENTS.md
4. **Add Tests**: Ensure comprehensive test coverage
5. **Consider Deployment**: Impact on container size, startup time, resources

### Common Development Tasks

#### Adding a New Voice Model

1. Update model download logic in `initialize_voice_engine.py`
2. Modify cache key generation for voice-specific caching
3. Add model validation and error handling
4. Update documentation and configuration examples

#### Implementing Multi-Voice Support

1. Extend `SynthesizeRequest` with voice parameter
2. Modify model loading to support multiple voices
3. Implement LRU cache for model management
4. Add RAM usage monitoring and limits

#### Adding API Versioning

1. Create versioned router modules (`app/v1/`, `app/v2/`)
2. Implement version-specific request/response models
3. Add backward compatibility layer
4. Update deployment and documentation

## Debugging

### Common Issues

1. **Model Download Failures**:
   ```bash
   # Check network connectivity and model names
   uv run python -c "import piper.download_voices; print(piper.download_voices.VOICE_ALIASES)"
   ```

2. **Valkey Connection Issues**:
   ```bash
   # Test Valkey connection
   valkey-cli -h localhost -p 6379 ping
   ```

3. **Memory Issues**:
   ```bash
   # Monitor memory usage
   docker stats  # For containerized development
   htop          # For local development
   ```

### Logging and Monitoring

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# View real-time logs
uv run uvicorn app.main:app --reload --log-level debug

# Test cache behavior
curl -H "user-token: DEBUG" -X POST \
  "http://localhost:8000/synthesizeSpeech" \
  -d '{"text": "test"}' -v
```

## Performance Testing

### Load Testing with wrk

```bash
# Install wrk (macOS)
brew install wrk

# Test cached requests
wrk -t4 -c100 -d30s \
  -H "user-token: DEBUG" \
  -H "Content-Type: application/json" \
  -s scripts/post_synthesis.lua \
  http://localhost:8000/synthesizeSpeech

# Test different text (cache misses)
wrk -t4 -c10 -d30s \
  -H "user-token: DEBUG" \
  -H "Content-Type: application/json" \
  -s scripts/random_text.lua \
  http://localhost:8000/synthesizeSpeech
```

### Benchmarking

```python
import asyncio
import time
import httpx

async def benchmark_synthesis(num_requests=100):
    """Benchmark synthesis performance."""
    async with httpx.AsyncClient() as client:
        start_time = time.time()

        tasks = []
        for i in range(num_requests):
            task = client.post(
                "http://localhost:8000/synthesizeSpeech",
                headers={"user-token": "DEBUG"},
                json={"text": f"Test message {i}"}
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        end_time = time.time()

        successful = sum(1 for r in responses if r.status_code == 200)
        print(f"Completed {successful}/{num_requests} requests in {end_time - start_time:.2f}s")
        print(f"Rate: {successful / (end_time - start_time):.2f} requests/second")

# Run benchmark
asyncio.run(benchmark_synthesis())
```

## Contributing

### Pull Request Process

1. Fork the repository
2. Create feature branch from `main`
3. Make changes following coding standards
4. Add/update tests and documentation
5. Ensure all checks pass (lint, type, test)
6. Submit PR with clear description
7. Address review feedback
8. Squash commits before merge

### Code Review Checklist

- [ ] Follows coding standards in AGENTS.md
- [ ] Includes comprehensive tests
- [ ] Updates relevant documentation
- [ ] Maintains backward compatibility
- [ ] Considers performance impact
- [ ] Handles errors gracefully
- [ ] Includes AIDEV anchor comments for complex logic

### Release Process

The project uses automated releases via GitHub Actions:

1. **Merge to main** triggers CI/CD pipeline
2. **Conventional commits** determine version bump
3. **Release Please** creates release PR
4. **Container image** built and pushed automatically
5. **Changelog** updated automatically

## IDE Setup

### VS Code

Recommended extensions:
- Python (Microsoft)
- Pylance (Microsoft)
- Ruff (Charlie Marsh)
- GitLens (GitKraken)

Settings (`.vscode/settings.json`):
```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.linting.enabled": true,
    "python.formatting.provider": "none",
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.codeActionsOnSave": {
            "source.organizeImports": true,
            "source.fixAll": true
        }
    },
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"]
}
```

### PyCharm

1. Configure interpreter: `.venv/bin/python`
2. Enable Ruff plugin
3. Set code style to match project settings
4. Configure test runner: pytest
