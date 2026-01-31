# Architecture Overview

The TTS Batch API is designed as a high-performance, containerized text-to-speech service built on modern Python async patterns.

## System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client App    │───▶│   TTS API       │───▶│   Redis Cache   │
│                 │    │   (FastAPI)     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   PIPER TTS     │
                       │   Engine        │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   ONNX Models   │
                       │   (Voice Data)  │
                       └─────────────────┘
```

## Core Components

### 1. FastAPI Web Server (`app/main.py`)

**Purpose**: RESTful API server handling TTS requests with authentication and caching

**Key Features**:
- Async request handling for high concurrency
- Token-based authentication via headers
- Automatic lifespan management for resources
- Structured error responses

**Critical Paths**:
- `/synthesizeSpeech` - Primary TTS endpoint
- `/health` - Container health checking

### 2. PIPER TTS Engine (`app/initialize_voice_engine.py`)

**Purpose**: Neural text-to-speech synthesis using ONNX models

**Key Features**:
- Auto-download missing voice models
- Configurable model storage directory
- Memory-efficient single model loading
- Fallback to home directory for read-only filesystems

**Model Management**:
- Models stored as `.onnx` files with `.json` configuration
- SHA256-based model integrity (future enhancement)
- Support for multiple voice models (planned)

### 3. Redis Caching Layer (`TTSCache` class)

**Purpose**: High-performance audio caching to minimize synthesis compute

**Caching Strategy**:
- **Key Generation**: SHA256 hash of `voice_id:text`
- **TTL Management**: Configurable expiration (default 7 days)
- **Cache-First Pattern**: Always check cache before synthesis
- **Async Operations**: Non-blocking Redis interactions

**Memory Efficiency**:
- Audio stored as compressed byte streams
- Automatic cleanup via Redis TTL
- Connection pooling for concurrent requests

### 4. Configuration System

**Environment-First Design**:
- All configuration via environment variables
- Container-friendly defaults
- Runtime validation for required settings

## Data Flow

### Successful Cache Hit
1. Client sends POST to `/synthesizeSpeech`
2. Authentication validation
3. Cache key generation from text
4. Redis lookup returns cached audio
5. Direct response with cached data

### Cache Miss - New Synthesis
1. Client sends POST to `/synthesizeSpeech`
2. Authentication validation
3. Cache key generation (cache miss)
4. PIPER TTS synthesis with loaded model
5. Audio data stored in Redis cache
6. Response with synthesized audio

## Performance Characteristics

### Latency Targets
- **Cache Hit**: <50ms (Redis lookup + network)
- **Cache Miss**: <2s (synthesis + caching + network)
- **Model Loading**: <10s (first request only)

### Throughput
- **Cached Requests**: 1000+ RPS (Redis-limited)
- **Synthesis Requests**: 10-50 RPS (CPU-limited)

### Memory Usage
- **Base Container**: ~200MB
- **Voice Model**: ~50-100MB per model
- **Redis Connection**: ~10MB

## Security Design

### Authentication
- Simple token-based auth via `user-token` header
- Single shared secret via `ALLOWED_USER_TOKEN`
- HTTP 403 for unauthorized requests

### Data Protection
- No persistent storage of user text
- Audio cache automatically expires
- No logging of user content (by design)

## Scalability Patterns

### Horizontal Scaling
- Stateless application design
- Shared Redis cache across instances
- Load balancer compatible

### Resource Constraints
- Single voice model per container (RAM management)
- Configurable cache TTL for storage efficiency
- Auto-cleanup of expired cache entries

## Future Architecture Considerations

### Multi-Voice Support
- **Challenge**: Memory management with multiple loaded models
- **Solution**: LRU model cache with configurable limits
- **Implementation**: Model loading/unloading based on usage patterns

### API Versioning
- **Current**: Direct endpoint `/synthesizeSpeech`
- **Planned**: Versioned paths `/v1/synthesizeSpeech`
- **Migration**: Backward compatibility during transition

### Monitoring Integration
- **Metrics**: Prometheus-compatible endpoints
- **Tracing**: OpenTelemetry support
- **Logging**: Structured JSON logs for aggregation
