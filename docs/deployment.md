# Deployment Guide

This guide covers deploying the TTS Batch API in various containerized environments, with a focus on Kubernetes deployment.

## Container Image

The API is distributed as a container image: `stkr22/tts-batch-api`

### Image Details
- **Base**: Python 3.12+ minimal image
- **Size**: ~500MB (includes PIPER TTS and dependencies)
- **Architecture**: Multi-arch support (amd64, arm64)
- **User**: Non-root user for security

## Quick Start Deployments

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  tts-api:
    image: stkr22/tts-batch-api:latest
    ports:
      - "8000:8000"
    environment:
      - ALLOWED_USER_TOKEN=your-secure-token-here
      - VALKEY_HOST=valkey
      - VALKEY_PORT=6379
      - TTS_MODEL=en_US-kathleen-low.onnx
      - LOG_LEVEL=INFO
    volumes:
      - tts_models:/app/assets
    depends_on:
      - valkey
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  valkey:
    image: valkey/valkey:8-alpine
    ports:
      - "6379:6379"
    volumes:
      - valkey_data:/data
    restart: unless-stopped
    command: valkey-server --appendonly yes

volumes:
  tts_models:
  valkey_data:
```

**Start the stack**:
```bash
docker-compose up -d
```

### Standalone Docker

```bash
# Start Valkey
docker run -d --name tts-valkey \
  -p 6379:6379 \
  valkey/valkey:8-alpine

# Start TTS API
docker run -d --name tts-api \
  -p 8000:8000 \
  -e ALLOWED_USER_TOKEN=your-secure-token \
  -e VALKEY_HOST=host.docker.internal \
  -e TTS_MODEL=en_US-kathleen-low.onnx \
  --link tts-valkey:valkey \
  stkr22/tts-batch-api:latest
```

## Kubernetes Deployment

### Namespace Setup

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tts-system
  labels:
    app.kubernetes.io/name: tts-batch-api
```

### ConfigMap and Secrets

```yaml
# config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tts-config
  namespace: tts-system
data:
  TTS_MODEL: "en_US-kathleen-low.onnx"
  VALKEY_HOST: "valkey-service"
  VALKEY_PORT: "6379"
  ENABLE_CACHE: "true"
  CACHE_TTL: "604800"
  LOG_LEVEL: "INFO"
  ASSETS_DIR: "/app/assets"

---
apiVersion: v1
kind: Secret
metadata:
  name: tts-secrets
  namespace: tts-system
type: Opaque
stringData:
  ALLOWED_USER_TOKEN: "your-secure-production-token"
  # Optional: Valkey password
  # VALKEY_PASSWORD: "valkey-secure-password"
```

### Valkey Deployment

```yaml
# valkey.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: valkey
  namespace: tts-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: valkey
  template:
    metadata:
      labels:
        app: valkey
    spec:
      containers:
      - name: valkey
        image: valkey/valkey:8-alpine
        ports:
        - containerPort: 6379
        command: ["valkey-server", "--appendonly", "yes"]
        volumeMounts:
        - name: valkey-data
          mountPath: /data
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: valkey-data
        persistentVolumeClaim:
          claimName: valkey-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: valkey-service
  namespace: tts-system
spec:
  selector:
    app: valkey
  ports:
  - port: 6379
    targetPort: 6379
  type: ClusterIP

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: valkey-pvc
  namespace: tts-system
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

### TTS API Deployment

```yaml
# tts-api.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tts-api
  namespace: tts-system
  labels:
    app.kubernetes.io/name: tts-batch-api
    app.kubernetes.io/version: "latest"
spec:
  replicas: 2
  selector:
    matchLabels:
      app: tts-api
  template:
    metadata:
      labels:
        app: tts-api
    spec:
      containers:
      - name: tts-api
        image: stkr22/tts-batch-api:latest
        ports:
        - containerPort: 8000
          name: http
        envFrom:
        - configMapRef:
            name: tts-config
        - secretRef:
            name: tts-secrets
        volumeMounts:
        - name: model-storage
          mountPath: /app/assets
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 3
        resources:
          requests:
            memory: "512Mi"
            cpu: "200m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: false
      volumes:
      - name: model-storage
        persistentVolumeClaim:
          claimName: tts-models-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: tts-api-service
  namespace: tts-system
spec:
  selector:
    app: tts-api
  ports:
  - port: 80
    targetPort: 8000
    name: http
  type: ClusterIP

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: tts-models-pvc
  namespace: tts-system
spec:
  accessModes:
    - ReadWriteMany  # Shared across pods
  resources:
    requests:
      storage: 2Gi
```

### Ingress Configuration

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tts-api-ingress
  namespace: tts-system
  annotations:
    kubernetes.io/ingress.class: "nginx"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "30"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "30"
spec:
  tls:
  - hosts:
    - tts.yourdomain.com
    secretName: tts-tls
  rules:
  - host: tts.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: tts-api-service
            port:
              number: 80
```

### Deploy to Kubernetes

```bash
# Apply all configurations
kubectl apply -f namespace.yaml
kubectl apply -f config.yaml
kubectl apply -f valkey.yaml
kubectl apply -f tts-api.yaml
kubectl apply -f ingress.yaml

# Check deployment status
kubectl -n tts-system get pods
kubectl -n tts-system get services
kubectl -n tts-system logs -l app=tts-api
```

## Helm Chart Deployment

A dedicated Helm chart is available in a separate repository for production deployments.

```bash
# Add the Helm repository
helm repo add stkr22 https://stkr22.github.io/helm-charts
helm repo update

# Install with custom values
helm install tts-api stkr22/tts-batch-api \
  --namespace tts-system \
  --create-namespace \
  --set auth.token="your-secure-token" \
  --set valkey.enabled=true \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host="tts.yourdomain.com"
```

## Production Considerations

### Resource Planning

**Minimum Requirements per Pod**:
- **CPU**: 200m (0.2 cores) baseline, 1000m (1 core) limit
- **Memory**: 512Mi baseline, 1Gi limit
- **Storage**: 2Gi for voice models (shared across pods)

**Scaling Considerations**:
- CPU-bound for synthesis (cache misses)
- Memory-bound for voice model loading
- I/O-bound for cache hits (Valkey performance)

### Security Hardening

1. **Use Secrets for Sensitive Data**:
   ```yaml
   env:
   - name: ALLOWED_USER_TOKEN
     valueFrom:
       secretKeyRef:
         name: tts-secrets
         key: token
   ```

2. **Network Policies**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: tts-network-policy
     namespace: tts-system
   spec:
     podSelector:
       matchLabels:
         app: tts-api
     policyTypes:
     - Ingress
     - Egress
     ingress:
     - from:
       - podSelector:
           matchLabels:
             app: ingress-nginx
     egress:
     - to:
       - podSelector:
           matchLabels:
             app: valkey
   ```

3. **Pod Security Standards**:
   ```yaml
   securityContext:
     runAsNonRoot: true
     runAsUser: 1000
     fsGroup: 1000
     allowPrivilegeEscalation: false
     readOnlyRootFilesystem: false
     capabilities:
       drop:
       - ALL
   ```

### Monitoring and Observability

**Health Checks**:
- Liveness probe on `/health` endpoint
- Readiness probe with 15s initial delay
- Startup probe for slow model loading

**Logging**:
- Structured JSON logs via `LOG_LEVEL=INFO`
- Log aggregation via Fluentd/Fluent Bit
- Centralized logging in ELK/Grafana Loki

**Metrics** (Future Enhancement):
- Prometheus metrics endpoint
- Custom metrics for synthesis latency
- Cache hit/miss ratios
- Active model memory usage

### Backup and Recovery

**Valkey Cache**:
- Periodic RDB snapshots
- AOF (Append Only File) for durability
- Cross-region replication for HA

**Voice Models**:
- Shared persistent volume
- Regular backup of model artifacts
- Version control for model updates

### High Availability

**Multi-Zone Deployment**:
```yaml
spec:
  replicas: 3
  template:
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - tts-api
              topologyKey: kubernetes.io/hostname
```

**Valkey HA**:
- Valkey Sentinel for automatic failover
- Valkey Cluster for horizontal scaling
- Backup Valkey instances in different zones
