# DialogChain - Flexible Dialog Processing Framework

🚀 **DialogChain** is a powerful and extensible framework for building, managing, and deploying dialog systems and conversational AI applications. It supports multiple programming languages and integrates with various NLP and ML models.

[![Python](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11-blue)](https://www.python.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Tests](https://github.com/dialogchain/python/actions/workflows/tests.yml/badge.svg)](https://github.com/dialogchain/python/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/dialogchain/python/graph/badge.svg?token=YOUR-TOKEN-HERE)](https://codecov.io/gh/dialogchain/python)

## 📖 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Documentation](#-documentation)
- [Examples](#-examples)
- [Architecture](#-architecture)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

- **Multi-language Support**: Write processors in Python, JavaScript, or any language with gRPC support
- **Extensible Architecture**: Easily add new input sources, processors, and output destinations
- **Asynchronous Processing**: Built on asyncio for high-performance dialog processing
- **YAML Configuration**: Define dialog flows and processing pipelines with simple YAML files
- **Built-in Processors**: Includes common NLP and ML model integrations
- **Monitoring & Logging**: Comprehensive logging and metrics out of the box
- **REST & gRPC APIs**: Easy integration with other services
- **Docker Support**: Containerized deployment options

## 🚀 Installation

### Prerequisites

- Python 3.8+
- Poetry (for development)
- Docker (optional, for containerized deployment)

### Using pip

```bash
pip install dialogchain
```

### From Source

```bash
git clone https://github.com/dialogchain/python
cd python
poetry install
```

## 🚀 Quick Start

1. Create a simple dialog configuration in `config.yaml`:

```yaml
version: "1.0"

pipeline:
  - name: greeting
    type: python
    module: dialogchain.processors.basic
    class: GreetingProcessor
    config:
      default_name: "User"
```

2. Run the dialog server:

```bash
dialogchain serve config.yaml
```

3. Send a request:

```bash
curl -X POST http://localhost:8000/process -H "Content-Type: application/json" -d '{"text": "Hello!"}'
```

## 📚 Documentation

For detailed documentation, please visit our [documentation site](https://dialogchain.github.io/python/).

## 📦 Project Structure

```
dialogchain/
├── src/
│   └── dialogchain/
│       ├── __init__.py
│       ├── engine.py          # Core processing engine
│       ├── processors/        # Built-in processors
│       ├── connectors/        # I/O connectors
│       └── utils/            # Utility functions
├── tests/                    # Test suite
├── examples/                 # Example configurations
└── docs/                     # Documentation
```

## 🧪 Testing

Run the complete test suite:

```bash
make test
```

Run specific test types:

```bash
# Unit tests
make test-unit

# Integration tests
make test-integration

# End-to-end tests
make test-e2e
```

Generate test coverage report:

```bash
make coverage
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For support, please open an issue in the [GitHub repository](https://github.com/dialogchain/python/issues).

## 🧪 Testing DialogChain

DialogChain includes a comprehensive test suite to ensure code quality and functionality. Here's how to run the tests and view logs:

### Running Tests

Run the complete test suite:

```bash
make test
```

Or run specific test types:

```bash
# Unit tests
make test-unit

# Integration tests
make test-integration

# End-to-end tests
make test-e2e
```

### Viewing Test Coverage

Generate a coverage report to see which parts of your code are being tested:

```bash
make coverage
```

This will generate an HTML report in the `htmlcov` directory.

### Viewing Logs

View the most recent logs from your application:

```bash
# Show last 50 lines from all log files
make logs

# Show a different number of lines
make logs LINES=100

# Specify a custom log directory
make logs LOG_DIR=/path/to/logs
```

### Linting and Code Style

Ensure your code follows the project's style guidelines:

```bash
# Run linters
make lint

# Automatically format your code
make format

# Check types
make typecheck
```

### Running in Docker

You can also run tests in a Docker container:

```bash
# Build the Docker image
docker build -t dialogchain .

# Run tests in the container
docker run --rm dialogchain make test
```

## 🔍 Network Scanning & Printing

DialogChain includes powerful network scanning capabilities to discover devices like cameras and printers on your local network.

### Scan for Network Devices

Scan your local network for various devices and services:

```bash
make scan-network
```

### Discover Cameras

Find RTSP cameras on your network:

```bash
make scan-cameras
```

### Discover Printers

List all available printers on your system:

```bash
make scan-printers
```

### Print a Test Page

Send a test page to your default printer:

```bash
make print-test
```

### Using the Network Scanner in Python

You can also use the network scanner directly in your Python code:

```python
from dialogchain.scanner import NetworkScanner
import asyncio

async def scan_network():
    scanner = NetworkScanner()
    
    # Scan for all services
    services = await scanner.scan_network()
    
    # Or scan for specific service types
    cameras = await scanner.scan_network(service_types=['rtsp'])
    
    for service in services:
        print(f"{service.ip}:{service.port} - {service.service} ({service.banner})")

# Run the scan
asyncio.run(scan_network())
```

## 🖨️ Printing Support

DialogChain includes basic printing capabilities using the CUPS (Common Unix Printing System) interface.

### Print Text

```python
import cups

def print_text(text, printer_name=None):
    conn = cups.Connection()
    printers = conn.getPrinters()
    
    if not printers:
        print("No printers available")
        return
        
    printer = printer_name or list(printers.keys())[0]
    job_id = conn.printFile(printer, "/dev/stdin", "DialogChain Print", {"raw": "True"}, text)
    print(f"Sent print job {job_id} to {printer}")

# Example usage
print_text("Hello from DialogChain!")
```

### Print from File

```python
def print_file(file_path, printer_name=None):
    conn = cups.Connection()
    printers = conn.getPrinters()
    
    if not printers:
        print("No printers available")
        return
        
    printer = printer_name or list(printers.keys())[0]
    job_id = conn.printFile(printer, file_path, "Document Print", {})
    print(f"Sent print job {job_id} to {printer}")

# Example usage
print_file("document.pdf")
```

## 📦 Installation

### Prerequisites
- Python 3.8+
- [Poetry](https://python-poetry.org/docs/#installation)

### Install with Poetry

1. Clone the repository:
   ```bash
   git clone https://github.com/dialogchain/python.git
   cd python
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Activate the virtual environment:
   ```bash
   poetry shell
   ```

### Development Setup

1. Install development and test dependencies:
   ```bash
   poetry install --with dev,test
   ```

2. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

3. Run tests:
   ```bash
   make test
   ```
   
   Or with coverage report:
   ```bash
   make coverage
   ```

## 🏗️ Project Structure

```
dialogchain/
├── src/
│   └── dialogchain/         # Main package
│       ├── __init__.py
│       ├── cli.py           # Command-line interface
│       ├── config.py        # Configuration handling
│       ├── connectors/      # Connector implementations
│       ├── engine.py        # Core engine
│       ├── exceptions.py    # Custom exceptions
│       ├── processors/      # Processor implementations
│       └── utils.py         # Utility functions
├── tests/                   # Test files
│   ├── unit/               # Unit tests
│   │   ├── core/           # Core functionality tests
│   │   ├── connectors/     # Connector tests
│   │   └── ...
│   └── integration/        # Integration tests
├── .github/                # GitHub workflows
├── docs/                   # Documentation
├── .gitignore
├── .pre-commit-config.yaml
├── Makefile               # Common development commands
├── pyproject.toml         # Project metadata and dependencies
└── README.md
```

## 🧪 Testing

Run the full test suite:
```bash
make test
```

Run specific test categories:
```bash
# Unit tests
make test-unit

# Integration tests
make test-integration

# With coverage report
make coverage
```

## 🧹 Code Quality

Format and check code style:
```bash
make format    # Auto-format code
make lint      # Run linters
make typecheck # Run type checking
make check-all # Run all checks
```

## 🚀 Quick Start

1. Create a configuration file `config.yaml`:
   ```yaml
   version: 1.0
   
   pipelines:
     - name: basic_dialog
       steps:
         - type: input
           name: user_input
           source: console
         - type: processor
           name: nlp_processor
           module: dialogchain.processors.nlp
           function: process_text
         - type: output
           name: response
           target: console
   ```

2. Run the dialog chain:
   ```bash
   poetry run dialogchain -c config.yaml
   ```

## ✨ Features

- **💬 Dialog Management**: Stateful conversation handling and context management
- **🤖 Multi-Language Support**: Python, Go, Rust, C++, Node.js processors
- **🔌 Flexible Connectors**: REST APIs, WebSockets, gRPC, MQTT, and more
- **🧠 ML/NLP Integration**: Built-in support for popular NLP libraries and models
- **⚙️ Simple Configuration**: YAML/JSON configuration with environment variables
- **🐳 Cloud Native**: Docker, Kubernetes, and serverless deployment ready
- **📊 Production Ready**: Monitoring, logging, and error handling
- **🧪 Comprehensive Testing**: Unit, integration, and end-to-end tests
- **🔍 Code Quality**: Type hints, linting, and code formatting
- **📈 Scalable**: Horizontal scaling for high-throughput applications

## 🛠️ Development

### Code Style

This project uses:
- [Black](https://github.com/psf/black) for code formatting
- [isort](https://pycqa.github.io/isort/) for import sorting
- [Flake8](https://flake8.pycqa.org/) for linting
- [mypy](http://mypy-lang.org/) for static type checking

### Development Commands

```bash
# Run tests with coverage
poetry run pytest --cov=dialogchain --cov-report=term-missing

# Format code
poetry run black .
poetry run isort .

# Lint code
poetry run flake8

# Type checking
poetry run mypy dialogchain
```

## 🏗️ Architecture

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────┐
│   Inputs    │    │   Processors     │    │  Outputs    │
├─────────────┤    ├──────────────────┤    ├─────────────┤
│ HTTP API    │───►│ NLP Processing   │───►│ REST API    │
│ WebSocket   │    │ Intent Detection │    │ WebSocket   │
│ gRPC        │    │ Entity Extraction│    │ gRPC        │
│ CLI         │    │ Dialog Management│    │ Message Bus │
│ Message Bus │    │ Response Gen     │    │ Logging     │
└─────────────┘    └──────────────────┘    └─────────────┘
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone https://github.com/dialogchain/python
cd python

# Install dependencies
poetry install

# Run the application
poetry run dialogchain --help
```

### 2. Configuration

Create your `.env` file:

```bash
# Copy template and edit
cp .env.example .env
```

Example `.env`:

```bash
CAMERA_USER=admin
CAMERA_PASS=your_password
CAMERA_IP=192.168.1.100
SMTP_USER=alerts@company.com
SMTP_PASS=app_password
SECURITY_EMAIL=security@company.com
```

### 3. Create Routes

Generate a configuration template:

```bash
dialogchain init --template camera --output my_config.yaml
```

Example route (simplified YAML):

```yaml
routes:
  - name: "smart_security_camera"
    from: "rtsp://{{CAMERA_USER}}:{{CAMERA_PASS}}@{{CAMERA_IP}}/stream1"

    processors:
      # Python: Object detection
      - type: "external"
        command: "python scripts/detect_objects.py"
        config:
          confidence_threshold: 0.6
          target_objects: ["person", "car"]

      # Go: Risk analysis
      - type: "external"
        command: "go run scripts/image_processor.go"
        config:
          threat_threshold: 0.7

      # Filter high-risk only
      - type: "filter"
        condition: "{{threat_level}} == 'high'"

    to:
      - "email://{{SMTP_SERVER}}:{{SMTP_PORT}}?user={{SMTP_USER}}&password={{SMTP_PASS}}&to={{SECURITY_EMAIL}}"
      - "http://webhook.company.com/security-alert"
```

### 4. Run

Run all routes
```bash
dialogchain run -c my_config.yaml
```

Run specific route
```bash
dialogchain run -c my_config.yaml --route smart_dialog_flow
```


Dry run to see what would execute
```bash
dialogchain run -c my_config.yaml --dry-run
```


```bash
 dialogchain run -c my_config.yaml --dry-run
🔍 DRY RUN - Configuration Analysis:
==================================================

📍 Route: front_door_camera
   From: rtsp://:@/stream1
   Processors:
     1. external
        Command: python -m ultralytics_processor
     2. filter
     3. transform
   To:
     • email://:?user=&password=&to=
```

## 📖 Detailed Usage

### Sources (Input)

| Source      | Example URL                             | Description         |
| ----------- | --------------------------------------- | ------------------- |
| RTSP Camera | `rtsp://user:pass@ip/stream1`           | Live video streams  |
| Timer       | `timer://5m`                            | Scheduled execution |
| File        | `file:///path/to/watch`                 | File monitoring     |
| gRPC        | `grpc://localhost:50051/Service/Method` | gRPC endpoints      |
| MQTT        | `mqtt://broker:1883/topic`              | MQTT messages       |

### Processors (Transform)

#### External Processors

Delegate to any programming language:

```yaml
processors:
  # Python ML inference
  - type: "external"
    command: "python scripts/detect_objects.py"
    input_format: "json"
    output_format: "json"
    config:
      model: "yolov8n.pt"
      confidence_threshold: 0.6

  # Go image processing
  - type: "external"
    command: "go run scripts/image_processor.go"
    config:
      thread_count: 4
      optimization: "speed"

  # Rust performance-critical tasks
  - type: "external"
    command: "cargo run --bin data_processor"
    config:
      batch_size: 32
      simd_enabled: true

  # C++ optimized algorithms
  - type: "external"
    command: "./bin/cpp_postprocessor"
    config:
      algorithm: "fast_nms"
      threshold: 0.85

  # Node.js business logic
  - type: "external"
    command: "node scripts/business_rules.js"
    config:
      rules_file: "security_rules.json"
```

#### Built-in Processors

```yaml
processors:
  # Filter messages
  - type: "filter"
    condition: "{{confidence}} > 0.7"

  # Transform output
  - type: "transform"
    template: "Alert: {{object_type}} detected at {{position}}"

  # Aggregate over time
  - type: "aggregate"
    strategy: "collect"
    timeout: "5m"
    max_size: 100
```

### Destinations (Output)

| Destination | Example URL                                                                | Description     |
| ----------- | -------------------------------------------------------------------------- | --------------- |
| Email       | `email://smtp.gmail.com:587?user={{USER}}&password={{PASS}}&to={{EMAILS}}` | SMTP alerts     |
| HTTP        | `http://api.company.com/webhook`                                           | REST API calls  |
| MQTT        | `mqtt://broker:1883/alerts/camera`                                         | MQTT publishing |
| File        | `file:///logs/alerts.log`                                                  | File logging    |
| gRPC        | `grpc://service:50051/AlertService/Send`                                   | gRPC calls      |

## 🛠️ Development

### Project Structure

```
dialogchain/
├── dialogchain/           # Python package
│   ├── cli.py             # Command line interface
│   ├── engine.py          # Main routing engine
│   ├── processors.py      # Processing components
│   └── connectors.py      # Input/output connectors
├── scripts/               # External processors
│   ├── detect_objects.py  # Python: YOLO detection
│   ├── image_processor.go # Go: Risk analysis
│   ├── health_check.go    # Go: Health monitoring
│   └── business_rules.js  # Node.js: Business logic
├── examples/              # Configuration examples
│   └── simple_routes.yaml # Sample routes
├── k8s/                   # Kubernetes deployment
│   └── deployment.yaml    # K8s manifests
├── Dockerfile             # Container definition
├── Makefile              # Build automation
└── README.md             # This file
```

### Building External Processors

```bash
# Build all processors
make build-all

# Build specific language
make build-go
make build-rust
make build-cpp

# Install dependencies
make install-deps
```

### Development Workflow

```bash
# Development environment
make dev

# Run tests
make test

# Lint code
make lint

# Build distribution
make build
```

## 🐳 Docker Deployment

### Build and Run

```bash
# Build image
make docker

# Run with Docker
docker run -it --rm \
  -v $(PWD)/examples:/app/examples \
  -v $(PWD)/.env:/app/.env \
  dialogchain:latest

# Or use Make
make docker-run
```

### Docker Compose (with dependencies)

```yaml
version: "3.8"
services:
  dialogchain:
    build: .
    environment:
      - CAMERA_IP=192.168.1.100
      - MQTT_BROKER=mqtt
    volumes:
      - ./examples:/app/examples
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

## ☸️ Kubernetes Deployment

```bash
# Deploy to Kubernetes
make deploy-k8s

# Or manually
kubectl apply -f k8s/

# Check status
kubectl get pods -n dialogchain

# View logs
kubectl logs -f deployment/dialogchain -n dialogchain
```

Features in Kubernetes:

- **Horizontal Pod Autoscaling**: Auto-scale based on CPU/memory/custom metrics
- **Resource Management**: CPU/memory limits and requests
- **Health Checks**: Liveness and readiness probes
- **Persistent Storage**: Shared volumes for model files and logs
- **Service Discovery**: Internal service communication
- **Monitoring**: Prometheus metrics integration

## 📊 Monitoring and Observability

### Built-in Metrics

```bash
# Health check endpoint
curl http://localhost:8080/health

# Metrics endpoint (Prometheus format)
curl http://localhost:8080/metrics

# Runtime statistics
curl http://localhost:8080/stats
```

### Logging

```bash
# View real-time logs
make logs

# Start monitoring dashboard
make monitor
```

### Performance Benchmarking

```bash
# Run benchmarks
make benchmark
```

## 🔧 Configuration Reference

### Environment Variables

```bash
# Camera settings
CAMERA_USER=admin
CAMERA_PASS=password
CAMERA_IP=192.168.1.100
CAMERA_NAME=front_door

# Email settings
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@company.com
SMTP_PASS=app_password
SECURITY_EMAIL=security@company.com

# Service URLs
WEBHOOK_URL=https://hooks.company.com
ML_GRPC_SERVER=localhost:50051
DASHBOARD_URL=https://dashboard.company.com

# MQTT settings
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_USER=dialogchain
MQTT_PASS=secret

# Advanced settings
MAX_CONCURRENT_ROUTES=10
DEFAULT_TIMEOUT=30
LOG_LEVEL=info
METRICS_ENABLED=true
```

### Route Configuration Schema

```yaml
routes:
  - name: "route_name" # Required: Route identifier
    from: "source_uri" # Required: Input source
    processors: # Optional: Processing pipeline
      - type: "processor_type"
        config: {}
    to: ["destination_uri"] # Required: Output destinations

# Global settings
settings:
  max_concurrent_routes: 10
  default_timeout: 30
  log_level: "info"
  metrics_enabled: true
  health_check_port: 8080

# Required environment variables
env_vars:
  - CAMERA_USER
  - SMTP_PASS
```

## 🎯 Use Cases

### 1. Smart Security System

- **Input**: RTSP cameras, motion sensors
- **Processing**: Python (YOLO), Go (risk analysis), Node.js (rules)
- **Output**: Email alerts, mobile push, dashboard

### 2. Industrial Quality Control

- **Input**: Factory cameras, sensor data
- **Processing**: Python (defect detection), C++ (performance), Rust (safety)
- **Output**: MQTT control, database, operator alerts

### 3. IoT Data Pipeline

- **Input**: MQTT sensors, HTTP APIs
- **Processing**: Go (aggregation), Python (analytics), Node.js (business logic)
- **Output**: Time-series DB, real-time dashboard, alerts

### 4. Media Processing Pipeline

- **Input**: File uploads, streaming video
- **Processing**: Python (ML inference), C++ (codec), Rust (optimization)
- **Output**: CDN upload, metadata database, webhooks

## 🔍 Troubleshooting

### Common Issues

#### Camera Connection Failed

```bash
# Test RTSP connection
ffmpeg -i rtsp://user:pass@ip/stream1 -frames:v 1 test.jpg

# Check network connectivity
ping camera_ip
telnet camera_ip 554
```

#### External Processor Errors

```bash
# Test processor manually
echo '{"test": "data"}' | python scripts/detect_objects.py --input /dev/stdin

# Check dependencies
which go python node cargo

# View processor logs
dialogchain run -c config.yaml --verbose
```

#### Performance Issues

```bash
# Monitor resource usage
htop

# Check route performance
make benchmark

# Optimize configuration
# - Reduce frame processing rate
# - Increase batch sizes
# - Use async processors
```

### Debug Mode

```bash
# Enable verbose logging
dialogchain run -c config.yaml --verbose

# Dry run to test configuration
dialogchain run -c config.yaml --dry-run

# Validate configuration
dialogchain validate -c config.yaml
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and add tests
4. Run checks: `make dev-workflow`
5. Commit changes: `git commit -m 'Add amazing feature'`
6. Push to branch: `git push origin feature/amazing-feature`
7. Open Pull Request

### Development Setup

```bash
# Clone and setup
git clone https://github.com/dialogchain/python
cd python
make dev

# Run tests
make test

For questions or support, please open an issue in the [issue tracker](https://github.com/taskinity/dialogchain/issues).

## 🔗 Related Projects

- **[Apache Camel](https://camel.apache.org/)**: Original enterprise integration framework
- **[GStreamer](https://gstreamer.freedesktop.org/)**: Multimedia framework
- **[Apache NiFi](https://nifi.apache.org/)**: Data flow automation
- **[Kubeflow](https://kubeflow.org/)**: ML workflows on Kubernetes
- **[TensorFlow Serving](https://tensorflow.org/tfx/serving)**: ML model serving

## 💡 Roadmap

- [ ] **Web UI**: Visual route designer and monitoring dashboard
- [ ] **More Connectors**: Database, cloud storage, message queues
- [ ] **Model Registry**: Integration with MLflow, DVC
- [ ] **Stream Processing**: Apache Kafka, Apache Pulsar support
- [ ] **Auto-scaling**: Dynamic processor scaling based on load
- [ ] **Security**: End-to-end encryption, authentication, authorization
- [ ] **Templates**: Pre-built templates for common use cases

---

**Built with ❤️ for the ML and multimedia processing community**

[⭐ Star us on GitHub](https://github.com/dialogchain/python) | [📖 Documentation](https://docs.dialogchain.org) | [💬 Community](https://discord.gg/dialogchain)
