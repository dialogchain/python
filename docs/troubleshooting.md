# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with Camel Router, from configuration problems to performance issues.

## Table of Contents

- [Common Issues](#common-issues)
- [Configuration Problems](#configuration-problems)
- [Connection Issues](#connection-issues)
- [Performance Problems](#performance-problems)
- [External Processor Issues](#external-processor-issues)
- [Deployment Issues](#deployment-issues)
- [Debugging Tools](#debugging-tools)
- [Monitoring and Logs](#monitoring-and-logs)

## Common Issues

### Issue: Route Not Starting

**Symptoms:**

- Route appears in configuration but doesn't process messages
- No error messages in logs
- Health check shows route as "stopped"

**Diagnosis:**

```bash
# Check route validation
dialogchain validate -c config.yaml

# Run in dry-run mode
dialogchain run -c config.yaml --dry-run

# Enable verbose logging
dialogchain run -c config.yaml --verbose
```

**Common Causes & Solutions:**

1. **Invalid URI format**

   ```yaml
   # ❌ Incorrect
   from: "rtsp:invalid-format"

   # ✅ Correct
   from: "rtsp://user:pass@host:554/stream1"
   ```

2. **Missing environment variables**

   ```bash
   # Check if variables are set
   echo $CAMERA_USER
   echo $CAMERA_PASS

   # Load .env file
   source .env
   ```

3. **Port conflicts**

   ```bash
   # Check if port is in use
   netstat -tulpn | grep :8080

   # Use different port
   dialogchain run -c config.yaml --port 8081
   ```

### Issue: Messages Not Being Processed

**Symptoms:**

- Source is connected but no messages flow through
- Processors are not being executed
- No output to destinations

**Diagnosis:**

```bash
# Check source connectivity
curl -f http://localhost:8080/health

# Monitor route metrics
curl http://localhost:8080/metrics | grep camel_router

# Check individual route status
curl http://localhost:8080/routes/status
```

**Solutions:**

1. **Check filter conditions**

   ```yaml
   # Debug filter condition
   - type: "filter"
     condition: "{{confidence}} > 0.7" # Make sure this evaluates correctly

   # Add debug processor before filter
   - type: "debug"
     prefix: "Before filter"
   - type: "filter"
     condition: "{{confidence}} > 0.7"
   ```

2. **Verify message format**

   ```python
   # In external processor, log input
   print(f"Input message: {json.dumps(input_data, indent=2)}")
   ```

3. **Check processor order**
   ```yaml
   processors:
     # Order matters - each processor receives output from previous
     - type: "external"
       command: "python detect.py"
     - type: "filter" # Receives output from detect.py
       condition: "{{detected}} == true"
     - type: "transform" # Receives filtered messages
       template: "Alert: {{message}}"
   ```

## Configuration Problems

### Invalid YAML Syntax

**Error Message:**

```
Error: YAML parsing failed: invalid syntax at line 15
```

**Solutions:**

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Use online YAML validator
# https://codebeautify.org/yaml-validator

# Check indentation (use spaces, not tabs)
cat -A config.yaml | grep -E '^\t'
```

### Variable Resolution Issues

**Error Message:**

```
Error: Environment variable CAMERA_USER not set
```

**Diagnosis:**

```bash
# Check required variables
dialogchain validate -c config.yaml

# List environment variables
env | grep CAMERA

# Check .env file
cat .env
```

**Solutions:**

```bash
# Set missing variables
export CAMERA_USER=admin
export CAMERA_PASS=password

# Use different .env file
dialogchain run -c config.yaml -e production.env

# Set default values in configuration
# Use Jinja2 default filter
from: "rtsp://{{CAMERA_USER|default('admin')}}:{{CAMERA_PASS}}@{{CAMERA_IP}}/stream1"
```

### Schema Validation Errors

**Error Message:**

```
Validation Error: Route 'test': Missing 'to' field
```

**Common Issues:**

```yaml
# ❌ Missing required fields
routes:
  - name: "incomplete_route"
    from: "timer://5s"
    # Missing 'to' field

# ❌ Invalid processor type
processors:
  - type: "invalid_type"  # Should be: external, filter, transform, aggregate

# ❌ Missing command for external processor
processors:
  - type: "external"
    # Missing 'command' field

# ✅ Complete and valid
routes:
  - name: "complete_route"
    from: "timer://5s"
    processors:
      - type: "external"
        command: "echo test"
    to: "log://"
```

## Connection Issues

### RTSP Camera Connection

**Error Message:**

```
Cannot connect to RTSP stream: rtsp://192.168.1.100/stream1
```

**Diagnosis:**

```bash
# Test RTSP connection manually
ffmpeg -i rtsp://user:pass@192.168.1.100:554/stream1 -frames:v 1 test.jpg

# Check network connectivity
ping 192.168.1.100
telnet 192.168.1.100 554

# Test with VLC or other RTSP client
vlc rtsp://user:pass@192.168.1.100:554/stream1
```

**Solutions:**

1. **Check credentials**

   ```yaml
   # Verify username/password
   from: "rtsp://{{CAMERA_USER}}:{{CAMERA_PASS}}@{{CAMERA_IP}}/stream1"
   ```

2. **Try different stream URLs**

   ```yaml
   # Common RTSP URL patterns
   from: "rtsp://user:pass@ip:554/stream1"     # Most common
   from: "rtsp://user:pass@ip:554/cam/realmonitor?channel=1&subtype=0"  # Dahua
   from: "rtsp://user:pass@ip:554/Streaming/Channels/101"  # Hikvision
   ```

3. **Network configuration**
   ```yaml
   # Add timeout and retry settings
   rtsp:
     url: "rtsp://user:pass@ip/stream1"
     timeout: 30
     reconnect_attempts: 5
   ```

### MQTT Connection Issues

**Error Message:**

```
MQTT connection failed: Connection refused
```

**Diagnosis:**

```bash
# Test MQTT connection
mosquitto_pub -h localhost -p 1883 -t test -m "hello"
mosquitto_sub -h localhost -p 1883 -t test

# Check MQTT broker status
docker logs mqtt-broker
systemctl status mosquitto
```

**Solutions:**

1. **Check broker configuration**

   ```yaml
   # Verify MQTT settings
   from: "mqtt://{{MQTT_BROKER}}:1883/topic/name"

   # Add authentication if required
   from: "mqtt://{{MQTT_USER}}:{{MQTT_PASS}}@{{MQTT_BROKER}}:1883/topic"
   ```

2. **Firewall and network**

   ```bash
   # Check if port is open
   nmap -p 1883 mqtt-broker-host

   # Allow MQTT port in firewall
   sudo ufw allow 1883
   ```

### HTTP/Email Connection Issues

**Error Message:**

```
HTTP destination error 503: Service Unavailable
SMTP authentication failed
```

**Diagnosis:**

```bash
# Test HTTP endpoint
curl -f http://webhook-url/endpoint

# Test SMTP connection
telnet smtp.gmail.com 587
openssl s_client -connect smtp.gmail.com:587 -starttls smtp
```

**Solutions:**

1. **HTTP issues**

   ```yaml
   # Add retries and timeout
   to: "http://api.example.com/webhook"
   # Check status codes
   # Add error handling in external processor
   ```

2. **Email issues**

   ```bash
   # Check credentials
   echo $SMTP_USER
   echo $SMTP_PASS

   # Use app passwords for Gmail
   # Enable 2FA and generate app password

   # Test with different SMTP settings
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587  # or 465 for SSL
   ```

## Performance Problems

### High Memory Usage

**Symptoms:**

- OOMKilled pods in Kubernetes
- Memory usage climbing continuously
- Slow processing performance

**Diagnosis:**

```bash
# Monitor memory usage
top -p $(pgrep dialogchain)
docker stats dialogchain

# Check memory limits
kubectl describe pod dialogchain-pod

# Profile Python memory usage
python -m memory_profiler scripts/detect_objects.py
```

**Solutions:**

1. **Optimize configuration**

   ```yaml
   settings:
     max_concurrent_routes: 5 # Reduce from default 10
     frame_skip_ratio: 5 # Process every 5th frame
     max_memory_usage: "1GB" # Set memory limit

   processors:
     - type: "aggregate"
       timeout: "30s" # Reduce aggregation window
       max_size: 50 # Reduce batch size
   ```

2. **External processor optimization**

   ```python
   # In Python processors
   import gc

   def process_frame(frame):
       # Process frame
       result = detect_objects(frame)

       # Force garbage collection
       gc.collect()

       return result
   ```

3. **Resource limits**
   ```yaml
   # Kubernetes deployment
   resources:
     requests:
       memory: "512Mi"
     limits:
       memory: "2Gi"
   ```

### High CPU Usage

**Symptoms:**

- CPU usage consistently above 80%
- Slow response times
- Processing delays

**Diagnosis:**

```bash
# Monitor CPU usage
top -p $(pgrep dialogchain)
htop

# Profile Python CPU usage
python -m cProfile -o profile.stats scripts/detect_objects.py
```

**Solutions:**

1. **Optimize processing**

   ```yaml
   settings:
     worker_threads: 4 # Match CPU cores
     async_processing: true # Enable async mode

   processors:
     - type: "external"
       command: "python detect.py"
       async: true # Don't wait for completion
   ```

2. **Use faster languages**
   ```yaml
   # Replace Python with Go/Rust for CPU-intensive tasks
   processors:
     - type: "external"
       command: "go run fast_processor.go" # Instead of Python
   ```

### Slow Processing

**Symptoms:**

- Messages pile up in queues
- High latency between input and output
- Timeouts in external processors

**Diagnosis:**

```bash
# Check processing times
curl http://localhost:8080/metrics | grep processing_time

# Monitor queue lengths
curl http://localhost:8080/metrics | grep queue_length

# Test external processors manually
time python scripts/detect_objects.py --input test.json
```

**Solutions:**

1. **Parallel processing**

   ```yaml
   # Increase concurrency
   settings:
     max_concurrent_routes: 10

   # Use batch processing
   processors:
     - type: "aggregate"
       strategy: "collect"
       max_size: 10 # Process in batches
       timeout: "5s"
   ```

2. **Optimize external processors**

   ```python
   # Use multiprocessing in Python
   from multiprocessing import Pool

   def process_batch(frames):
       with Pool(4) as pool:
           results = pool.map(detect_objects, frames)
       return results
   ```

## External Processor Issues

### Command Not Found

**Error Message:**

```
External command failed: python: command not found
External command failed: go: command not found
```

**Solutions:**

1. **Check PATH**

   ```bash
   # Verify commands are available
   which python
   which go
   which node

   # Add to PATH if needed
   export PATH=/usr/local/bin:$PATH
   ```

2. **Use full paths**

   ```yaml
   processors:
     - type: "external"
       command: "/usr/bin/python3 /app/scripts/detect.py"
   ```

3. **Docker environment**
   ```dockerfile
   # In Dockerfile, ensure tools are installed
   RUN apt-get update && apt-get install -y python3 golang nodejs
   ```

### Import/Module Errors

**Error Message:**

```
ModuleNotFoundError: No module named 'ultralytics'
ImportError: cannot import name 'YOLO'
```

**Solutions:**

1. **Install dependencies**

   ```bash
   # Python dependencies
   pip install ultralytics opencv-python

   # Go dependencies
   go mod tidy

   # Node.js dependencies
   npm install
   ```

2. **Virtual environment**

   ```bash
   # Use virtual environment
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Docker dependencies**
   ```dockerfile
   # Install in Docker image
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   ```

### Timeout Issues

**Error Message:**

```
External processor timeout after
```
