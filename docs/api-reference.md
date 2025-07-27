# API Reference

Complete reference for the TTS Batch API endpoints and data models.

## Base URL

```
http://localhost:8000  # Local development
https://your-domain.com  # Production deployment
```

## Authentication

All API endpoints require authentication via the `user-token` header:

```bash
curl -H "user-token: your-secret-token" ...
```

**Response Codes**:
- `403 Forbidden` - Invalid or missing token
- `200 OK` - Valid authentication

## Endpoints

### POST /synthesizeSpeech

Convert text to speech audio using the configured voice model.

#### Request

**Headers**:
- `user-token` (required): Authentication token
- `Content-Type`: `application/json`

**Body**:
```json
{
  "text": "Hello, this is a test message"
}
```

**Parameters**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Text to convert to speech (max ~500 characters recommended) |

#### Response

**Success (200 OK)**:
- **Content-Type**: `audio/x-raw`
- **Headers**: `Content-Length` with audio byte size
- **Body**: Raw audio data (16-bit PCM, 22050 Hz mono)

**Error Responses**:
- `403 Forbidden` - Invalid authentication token
- `500 Internal Server Error` - Cache not initialized or synthesis failure

#### Example

```bash
# Basic synthesis request
curl -X POST "http://localhost:8000/synthesizeSpeech" \
  -H "user-token: your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world"}' \
  --output hello.wav

# Check response headers
curl -I -X POST "http://localhost:8000/synthesizeSpeech" \
  -H "user-token: your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world"}'
```

#### Audio Format Details

- **Encoding**: 16-bit signed PCM
- **Sample Rate**: 22050 Hz (configurable via model)
- **Channels**: Mono (1 channel)
- **Byte Order**: Little-endian
- **File Format**: Raw audio (no headers)

To convert to standard formats:

```bash
# Convert to WAV using ffmpeg
ffmpeg -f s16le -ar 22050 -ac 1 -i audio.raw audio.wav

# Convert to MP3
ffmpeg -f s16le -ar 22050 -ac 1 -i audio.raw -b:a 128k audio.mp3
```

### GET /health

Health check endpoint for container orchestration.

#### Request

No authentication required.

#### Response

**Success (200 OK)**:
```json
{
  "status": "healthy"
}
```

#### Example

```bash
curl http://localhost:8000/health
```

## Data Models

### SynthesizeRequest

```json
{
  "text": "string"
}
```

**Validation Rules**:
- `text` must be non-empty string
- Recommended maximum length: 500 characters
- Special characters and unicode supported

### Error Response

```json
{
  "detail": "string"
}
```

**Common Error Messages**:
- `"Forbidden"` - Authentication failure
- `"Cache not initialized"` - Internal server error

## Rate Limiting

Currently no explicit rate limiting is implemented. Performance characteristics:

- **Cached requests**: ~1000+ requests/second
- **New synthesis**: ~10-50 requests/second (depending on text length)

For production use, implement rate limiting at the load balancer or API gateway level.

## Caching Behavior

The API implements intelligent caching:

1. **Cache Key**: Generated from voice model and input text
2. **Cache Duration**: 7 days (configurable via `CACHE_TTL`)
3. **Cache Hit**: Immediate response with cached audio
4. **Cache Miss**: Synthesis + caching + response

**Cache Considerations**:
- Identical text returns identical audio (deterministic)
- Text case and whitespace sensitive
- Different voice models create separate cache entries

## Integration Examples

### Python Client

```python
import httpx

class TTSClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token
    
    async def synthesize(self, text: str) -> bytes:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/synthesizeSpeech",
                headers={"user-token": self.token},
                json={"text": text}
            )
            response.raise_for_status()
            return response.content

# Usage
client = TTSClient("http://localhost:8000", "your-token")
audio_data = await client.synthesize("Hello world")
```

### JavaScript/Node.js Client

```javascript
const axios = require('axios');
const fs = require('fs');

async function synthesizeSpeech(text, token, baseUrl = 'http://localhost:8000') {
    try {
        const response = await axios.post(
            `${baseUrl}/synthesizeSpeech`,
            { text },
            {
                headers: {
                    'user-token': token,
                    'Content-Type': 'application/json'
                },
                responseType: 'arraybuffer'
            }
        );
        
        return Buffer.from(response.data);
    } catch (error) {
        console.error('TTS request failed:', error.response?.status, error.response?.data);
        throw error;
    }
}

// Usage
synthesizeSpeech("Hello world", "your-token")
    .then(audioData => fs.writeFileSync('output.raw', audioData))
    .catch(console.error);
```