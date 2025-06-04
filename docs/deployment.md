# Deployment Guide

This guide covers various deployment options for Camel Router, from local development to production Kubernetes clusters.

## Table of Contents

- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Docker Compose](#docker-compose)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Cloud Platforms](#cloud-platforms)
- [Monitoring and Observability](#monitoring-and-observability)
- [Security Considerations](#security-considerations)
- [Scaling and Performance](#scaling-and-performance)

## Local Development

### Prerequisites

- Python 3.8+
- Go 1.21+
- Node.js 16+
- Rust (optional)
- Docker (optional)

### Quick Setup

```bash
# Clone repository
git clone https://github.com/taskinity/dialogchain
cd dialogchain

# Install and setup
make quickstart

# Run with sample configuration
dialogchain run -c examples/simple_routes.yaml
```

### Development Environment

```bash
# Install in development mode
make dev

# Run tests
make test

# Build external processors
make build-all

# Start with hot reload (if using file watcher)
dialogchain run -c config.yaml --verbose
```

## Docker Deployment

### Building Docker Image

```bash
# Build production image
docker build -t dialogchain:latest .

# Build development image
docker build --target dev -t dialogchain:dev .

# Multi-platform build
docker buildx build --platform linux/amd64,linux/arm64 -t dialogchain:latest .
```

### Running with Docker

```bash
# Basic run
docker run -d \
  --name dialogchain \
  -p 8080:8080 \
  -v $(pwd)/examples:/app/examples \
  -v $(pwd)/.env:/app/.env \
  dialogchain:latest

# With custom configuration
docker run -d \
  --name dialogchain \
  -p 8080:8080 \
  -v $(pwd)/my-config.yaml:/app/config.yaml \
  -v $(pwd)/.env:/app/.env \
  dialogchain:latest \
  dialogchain run -c config.yaml

# Development mode with volumes
docker run -it --rm \
  -p 8080:8080 \
  -v $(pwd):/app \
  -w /app \
  dialogchain:dev \
  bash
```

### Docker Image Variants

#### Production Image (`dialogchain:latest`)

- Optimized for size and security
- Multi-stage build
- Non-root user
- Minimal dependencies

#### Development Image (`dialogchain:dev`)

- Includes development tools
- Debugging utilities
- Full build environment

## Docker Compose

### Basic Setup

```yaml
version: "3.8"

services:
  dialogchain:
    image: dialogchain:latest
    ports:
      - "8080:8080"
    environment:
      - CAMERA_IP=192.168.1.100
      - MQTT_BROKER=mqtt
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    depends_on:
      - mqtt
      - redis

  mqtt:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### Full Stack with Monitoring

```yaml
version: "3.8"

services:
  dialogchain:
    image: dialogchain:latest
    ports:
      - "8080:8080"
    environment:
      - MQTT_BROKER=mqtt
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    depends_on:
      - mqtt
      - redis
      - postgres

  mqtt:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: DialogChain
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres-data:/var/lib/postgresql/data

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana

volumes:
  redis-data:
  postgres-data:
  grafana-data:
```

### Running Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f dialogchain

# Scale services
docker-compose up -d --scale dialogchain=3

# Stop services
docker-compose down

# Clean up
docker-compose down -v
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.19+)
- kubectl configured
- Helm 3.x (optional)

### Quick Deployment

```bash
# Apply manifests
kubectl apply -f k8s/

# Check deployment
kubectl get pods -n dialogchain

# View logs
kubectl logs -f deployment/dialogchain -n dialogchain

# Port forward for testing
kubectl port-forward service/dialogchain-service 8080:8080 -n dialogchain
```

### Namespace Setup

```bash
# Create namespace
kubectl create namespace dialogchain

# Set default namespace
kubectl config set-context --current --namespace=dialogchain
```

### Configuration Management

```bash
# Create ConfigMap from files
kubectl create configmap dialogchain-config \
  --from-file=routes.yaml=examples/simple_routes.yaml \
  -n dialogchain

# Create Secret for sensitive data
kubectl create secret generic dialogchain-secrets \
  --from-literal=CAMERA_PASS=your_password \
  --from-literal=SMTP_PASS=your_smtp_password \
  -n dialogchain
```

### Persistent Storage

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: dialogchain-storage
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 50Gi
  storageClassName: fast-ssd
```

### Ingress Configuration

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dialogchain-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
    - hosts:
        - dialogchain.yourdomain.com
      secretName: dialogchain-tls
  rules:
    - host: dialogchain.yourdomain.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: dialogchain-service
                port:
                  number: 8080
```

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: dialogchain-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: dialogchain
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

## Cloud Platforms

### AWS EKS

```bash
# Create EKS cluster
eksctl create cluster --name dialogchain --region us-west-2

# Configure kubectl
aws eks update-kubeconfig --region us-west-2 --name dialogchain

# Deploy
kubectl apply -f k8s/
```

### Google GKE

```bash
# Create GKE cluster
gcloud container clusters create dialogchain \
  --zone us-central1-a \
  --machine-type n1-standard-2 \
  --num-nodes 3

# Get credentials
gcloud container clusters get-credentials dialogchain --zone us-central1-a

# Deploy
kubectl apply -f k8s/
```

### Azure AKS

```bash
# Create resource group
az group create --name dialogchain-rg --location eastus

# Create AKS cluster
az aks create \
  --resource-group dialogchain-rg \
  --name dialogchain \
  --node-count 3 \
  --enable-addons monitoring \
  --generate-ssh-keys

# Get credentials
az aks get-credentials --resource-group dialogchain-rg --name dialogchain

# Deploy
kubectl apply -f k8s/
```

### Serverless Deployments

#### AWS Lambda (with Serverless Framework)

```yaml
# serverless.yml
service: dialogchain-lambda

provider:
  name: aws
  runtime: python3.9
  environment:
    STAGE: ${self:provider.stage}

functions:
  processor:
    handler: lambda_handler.handler
    events:
      - schedule: rate(5 minutes)
    environment:
      CONFIG_FILE: config.yaml

plugins:
  - serverless-python-requirements
```

#### Google Cloud Functions

```bash
# Deploy function
gcloud functions deploy dialogchain-processor \
  --runtime python39 \
  --trigger-http \
  --entry-point process_route \
  --set-env-vars CONFIG_FILE=config.yaml
```

## Monitoring and Observability

### Metrics Collection

```yaml
# ServiceMonitor for Prometheus
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: dialogchain-metrics
spec:
  selector:
    matchLabels:
      app: dialogchain
  endpoints:
    - port: metrics
      interval: 30s
      path: /metrics
```

### Logging

```yaml
# Fluentd DaemonSet for log collection
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd-dialogchain
spec:
  selector:
    matchLabels:
      name: fluentd-dialogchain
  template:
    spec:
      containers:
        - name: fluentd
          image: fluent/fluentd-kubernetes-daemonset:v1-debian-elasticsearch
          env:
            - name: ELASTICSEARCH_HOST
              value: "elasticsearch.logging.svc.cluster.local"
```

### Distributed Tracing

```yaml
# Jaeger deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jaeger
spec:
  template:
    spec:
      containers:
        - name: jaeger
          image: jaegertracing/all-in-one:latest
          ports:
            - containerPort: 16686
            - containerPort: 14268
```

### Alerting Rules

```yaml
# PrometheusRule for alerting
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: dialogchain-alerts
spec:
  groups:
    - name: dialogchain
      rules:
        - alert: DialogChainDown
          expr: up{job="dialogchain"} == 0
          for: 1m
          labels:
            severity: critical
          annotations:
            summary: "Camel Router is down"
            description: "Camel Router has been down for more than 1 minute"

        - alert: HighErrorRate
          expr: rate(camel_router_errors_total[5m]) > 0.1
          for: 2m
          labels:
            severity: warning
          annotations:
            summary: "High error rate detected"
            description: "Error rate is {{ $value }} errors per second"
```

## Security Considerations

### Network Security

```yaml
# NetworkPolicy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dialogchain-network-policy
spec:
  podSelector:
    matchLabels:
      app: dialogchain
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: monitoring
      ports:
        - protocol: TCP
          port: 9090
  egress:
    - {} # Allow all egress (customize as needed)
```

### Pod Security

```yaml
# SecurityContext
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL
    add:
      - NET_BIND_SERVICE
```

### Secret Management

```bash
# Using Kubernetes secrets
kubectl create secret generic dialogchain-secrets \
  --from-literal=database-password=super-secret \
  --from-literal=api-key=abc123

# Using external secret management (e.g., Vault)
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace
```

### RBAC Configuration

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: dialogchain-role
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list", "watch"]
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch", "update"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dialogchain-binding
subjects:
  - kind: ServiceAccount
    name: dialogchain-sa
roleRef:
  kind: Role
  name: dialogchain-role
  apiGroup: rbac.authorization.k8s.io
```

## Scaling and Performance

### Vertical Scaling

```yaml
# Resource requests and limits
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

### Horizontal Scaling

```yaml
# HPA with custom metrics
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: dialogchain-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: dialogchain
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: messages_per_second
        target:
          type: AverageValue
          averageValue: "100"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Percent
          value: 50
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
```

### Performance Optimization

#### Configuration Tuning

```yaml
settings:
  max_concurrent_routes: 20
  default_timeout: 30
  frame_skip_ratio: 2
  max_memory_usage: "4GB"
  worker_threads: 8
  buffer_size: 1024
  batch_processing: true
  async_io: true
```

#### Resource Allocation

```yaml
# Node affinity for performance
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: node-type
              operator: In
              values:
                - compute-optimized
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
              - key: app
                operator: In
                values:
                  - dialogchain
          topologyKey: kubernetes.io/hostname
```

### Caching Strategies

```yaml
# Redis for caching
redis:
  enabled: true
  host: redis-cluster
  port: 6379
  db: 0
  ttl: 3600
  max_connections: 100

# In-memory caching
cache:
  enabled: true
  max_size: 1000
  ttl: 300
```

## Troubleshooting

### Common Issues

#### Pod CrashLoopBackOff

```bash
# Check pod logs
kubectl logs pod-name -n dialogchain

# Describe pod for events
kubectl describe pod pod-name -n dialogchain

# Check resource constraints
kubectl top pod pod-name -n dialogchain
```

#### Configuration Issues

```bash
# Validate configuration
kubectl exec -it pod-name -n dialogchain -- dialogchain validate -c /app/config/routes.yaml

# Check ConfigMap
kubectl get configmap dialogchain-config -o yaml -n dialogchain

# Test connectivity
kubectl exec -it pod-name -n dialogchain -- curl http://external-service:8080/health
```

#### Performance Issues

```bash
# Check resource usage
kubectl top pods -n dialogchain

# Check HPA status
kubectl get hpa -n dialogchain

# Monitor metrics
kubectl port-forward service/dialogchain-service 9090:9090 -n dialogchain
```

### Debug Mode

```yaml
# Enable debug logging
env:
  - name: LOG_LEVEL
    value: "debug"
  - name: DEBUG_MODE
    value: "true"

# Add debug sidecar
containers:
  - name: debug
    image: nicolaka/netshoot
    command: ["sleep", "infinity"]
```

### Health Checks

```yaml
# Comprehensive health checks
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  successThreshold: 1
  failureThreshold: 3

startupProbe:
  httpGet:
    path: /startup
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 30
```

## Backup and Recovery

### Configuration Backup

```bash
# Backup ConfigMaps and Secrets
kubectl get configmap dialogchain-config -o yaml > backup/configmap.yaml
kubectl get secret dialogchain-secrets -o yaml > backup/secrets.yaml

# Backup entire namespace
kubectl get all,configmap,secret -n dialogchain -o yaml > backup/namespace-backup.yaml
```

### Data Backup

```bash
# Backup persistent volumes
kubectl get pv -o yaml > backup/persistent-volumes.yaml

# Create volume snapshots (if supported)
kubectl create -f volume-snapshot.yaml
```

### Disaster Recovery

```bash
# Restore from backup
kubectl apply -f backup/

# Restore specific components
kubectl apply -f backup/configmap.yaml
kubectl apply -f backup/secrets.yaml

# Scale deployment
kubectl scale deployment dialogchain --replicas=3 -n dialogchain
```

## CI/CD Integration

### GitOps with ArgoCD

```yaml
# Application manifest
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: dialogchain
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/taskinity/dialogchain
    targetRevision: main
    path: k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: dialogchain
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### Helm Deployment

```bash
# Install with Helm
helm repo add dialogchain https://charts.dialogchain.org
helm install dialogchain dialogchain/dialogchain \
  --namespace dialogchain \
  --create-namespace \
  --set image.tag=v1.0.0 \
  --set config.cameraIp=192.168.1.100

# Upgrade
helm upgrade dialogchain dialogchain/dialogchain \
  --set image.tag=v1.1.0

# Rollback
helm rollback dialogchain 1
```

### Continuous Deployment

```yaml
# GitHub Actions deployment
- name: Deploy to Kubernetes
  run: |
    kubectl set image deployment/dialogchain \
      dialogchain=ghcr.io/${{ github.repository }}:${{ github.sha }} \
      -n dialogchain
    kubectl rollout status deployment/dialogchain -n dialogchain
```

## Best Practices

### Resource Management

- Set appropriate resource requests and limits
- Use HPA for automatic scaling
- Monitor resource usage continuously
- Implement proper garbage collection

### Security

- Use least privilege principle
- Implement network policies
- Regularly update base images
- Scan for vulnerabilities

### Monitoring

- Implement comprehensive health checks
- Set up alerting for critical metrics
- Use distributed tracing
- Monitor business metrics

### Configuration

- Use GitOps for configuration management
- Implement configuration validation
- Use secrets for sensitive data
- Version control all configurations

### Testing

- Implement integration tests
- Use staging environments
- Perform load testing
- Test disaster recovery procedures

This deployment guide provides comprehensive coverage of deploying Camel Router across different environments, from local development to production Kubernetes clusters, with proper security, monitoring, and scaling considerations.
