# DialogChain - Flexible Dialog Processing Framework
# Makefile for development and deployment

# Logging configuration
LOG_LEVEL ?= INFO
LOG_FILE ?= logs/dialogchain.log
DB_LOG_FILE ?= logs/dialogchain.db
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

.PHONY: help install dev test clean build docker run-example lint docs \
        test-unit test-integration test-e2e coverage typecheck format check-codestyle \
        check-all pre-commit-install setup-dev-env docs-serve docs-clean \
        publish testpublish version

# Default target
help:
	@echo "DialogChain - Flexible Dialog Processing Framework"
	@echo ""
	@echo "Available commands:"
	@echo "  install          - Install the package and dependencies"
	@echo "  dev              - Install in development mode"
	@echo "  test             - Run tests"
	@echo "  lint             - Run linting and format checks"
	@echo "  clean            - Clean build artifacts"
	@echo "  build            - Build distribution packages"
	@echo "  publish          - Publish to PyPI (requires PYPI_TOKEN)"
	@echo "  testpublish      - Publish to TestPyPI (for testing)"
	@echo "  version          - Bump version (use: make version PART=major|minor|patch)"
	@echo "  docker           - Build Docker image"
	@echo "  run-example      - Run an example (use EXAMPLE=name)"
	@echo "  list-examples    - List available examples"
	@echo "  logs             - View recent logs (use: make logs LINES=50)"
	@echo "  view-logs        - View logs for running example"
	@echo "  stop-example     - Stop a running example"
	@echo "  log-level        - Set log level (use: make log-level LEVEL=DEBUG)"
	@echo "  log-db           - View database logs (use: make log-db LIMIT=50)"
	@echo "  log-tail         - Follow log file in real-time"
	@echo "  log-clear        - Clear log files"
	@echo "  docs             - Generate documentation"
	@echo "  setup-env        - Create example .env file"
	@echo ""
	@echo "Testing commands:"
	@echo "  test-unit        - Run unit tests"
	@echo "  test-integration - Run integration tests"
	@echo "  test-e2e         - Run end-to-end tests"
	@echo "  coverage         - Generate test coverage report"

# Installation
install:
	pip install -e .
	pip install python-nmap opencv-python pycups
	@echo "✅ DialogChain installed"

venv:
	python3 -m venv venv
	source venv/bin/activate
	@echo "✅ Virtual environment created"

dev: install
	pip install -e ".[dev]"
	@echo "✅ Development environment ready"

# Dependencies for different languages
install-deps:
	@echo "Installing dependencies for external processors..."
	# Python NLP dependencies
	pip install transformers spacy nltk

	# Check if Go is installed (optional)
	@which go > /dev/null && echo "✅ Go found: $$(go version)" || echo "ℹ️  Go not found. Install from https://golang.org/dl/ if needed"

	# Check if Node.js is installed (optional)
	@which node > /dev/null && echo "✅ Node.js found: $$(node --version)" || echo "ℹ️  Node.js not found. Install from https://nodejs.org/ if needed"

	# Check if Rust is installed
	@which cargo > /dev/null || (echo "⚠️  Rust not found. Install from https://rustup.rs/")
	@which cargo > /dev/null && echo "✅ Rust found: $$(cargo --version)"

# Development
test: venv test-unit test-integration test-e2e

# Run unit tests with logging
test-unit:
	@mkdir -p logs
	@echo "🔍 Running unit tests with log level: $(LOG_LEVEL)"
	@PYTHONPATH=./src pytest tests/unit/ -v \
		--log-cli-level=$(LOG_LEVEL) \
		--log-file=$(LOG_FILE) \
		--log-file-level=$(LOG_LEVEL) \
		--log-file-format="%(asctime)s - %(name)s - %(levelname)s - %(message)s" \
		--cov=src/dialogchain \
		--cov-report=term-missing
	@echo "✅ Unit tests completed - Logs saved to $(LOG_FILE)"

# Run integration tests
test-integration:
	@pytest tests/integration/ -v --cov=src/dialogchain --cov-append
	@echo "✅ Integration tests completed"

# Run end-to-end tests
test-e2e:
	@pytest tests/e2e/ -v --cov=src/dialogchain --cov-append
	@echo "✅ End-to-end tests completed"

# Run tests with coverage report
coverage:
	@coverage erase
	@coverage run -m pytest
	@coverage report -m
	@coverage html
	@echo "📊 Coverage report available at htmlcov/index.html"

# Run type checking
typecheck:
	@mypy src/dialogchain/
	@echo "✅ Type checking completed"

# Logging commands
log-level:
	@if [ -z "$(LEVEL)" ]; then \
		echo "Current log level: $(LOG_LEVEL)"; \
		echo "Usage: make log-level LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL"; \
	else \
		sed -i.bak 's/^LOG_LEVEL = .*/LOG_LEVEL = $(LEVEL)/' Makefile && \
		rm -f Makefile.bak && \
		echo "✅ Log level set to $(LEVEL)"; \
	fi

log-db:
	@mkdir -p logs
	@echo "📋 Displaying last $(or $(LIMIT), 50) database log entries:"
	@python -c "from dialogchain.utils.logger import display_recent_logs; display_recent_logs(limit=$(or $(LIMIT), 50))"

log-tail:
	@echo "📜 Tailing log file: $(LOG_FILE)"
	@tail -f $(LOG_FILE)

log-clear:
	@rm -f $(LOG_FILE) $(DB_LOG_FILE)
	@mkdir -p logs
	@touch $(LOG_FILE) $(DB_LOG_FILE)
	@echo "🧹 Log files cleared"

# Run all linters
lint:
	@echo "🔍 Running flake8..."
	@flake8 src/dialogchain/ tests/
	@echo "🎨 Checking code formatting with black..."
	@black --check src/dialogchain/ tests/
	@echo "📝 Checking import ordering..."
	@isort --check-only --profile black src/dialogchain/ tests/
	@echo "✅ Linting completed"

# Format code
format:
	@echo "🎨 Formatting code with black..."
	@black src/dialogchain/ tests/
	@echo "📝 Sorting imports..."
	@isort --profile black src/dialogchain/ tests/
	@echo "✅ Code formatted"

# Check code style without making changes
check-codestyle:
	@black --check --diff src/dialogchain/ tests/
	@isort --check-only --profile black src/dialogchain/ tests/


# Run all checks (lint, typecheck, test)
check-all: lint typecheck test
	@echo "✨ All checks passed!"

# Install pre-commit hooks
pre-commit-install:
	@pre-commit install
	@pre-commit install --hook-type pre-push
	@echo "✅ Pre-commit hooks installed"

# Setup development environment
setup-dev-env: install pre-commit-install
	@echo "🚀 Development environment ready!"

# Build
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	@echo "✅ Cleaned build artifacts"

build: clean
	poetry build
	@echo "✅ Distribution packages built"

# Version management
version:
	@if [ -z "$(PART)" ]; then \
		echo "Error: Please specify version part with PART=patch|minor|major"; \
		exit 1; \
	fi
	@echo "Bumping $$(poetry version $(PART) --dry-run) → $$(poetry version $(PART))"
	git add pyproject.toml
	git commit -m "Bump version to $$(poetry version --short)"
	git tag -a "v$$(poetry version --short)" -m "Version $$(poetry version --short)"
	@echo "✅ Version bumped and tagged. Don't forget to push with tags: git push --follow-tags"

# View recent logs from the application
LINES ?= 50  # Default number of lines to show
LOG_DIR ?= logs  # Default log directory

logs:
	@echo "📋 Showing last $(LINES) lines of logs from $(LOG_DIR)/"
	@if [ -d "$(LOG_DIR)" ]; then \
		find "$(LOG_DIR)" -type f -name "*.log" -exec sh -c 'echo "\n📄 {}:"; tail -n $(LINES) {}' \; 2>/dev/null || echo "No log files found in $(LOG_DIR)/"; \
	else \
		echo "Log directory $(LOG_DIR)/ does not exist"; \
	fi

# Helper to get PYPI_TOKEN from files
define get_pypi_token
$(shell \
    if [ -f "${HOME}/.pypirc" ]; then \
        grep -A 2 '\[pypi\]' "${HOME}/.pypirc" 2>/dev/null | grep 'token = ' | cut -d' ' -f3; \
    elif [ -f ".pypirc" ]; then \
        grep -A 2 '\[pypi\]' ".pypirc" 2>/dev/null | grep 'token = ' | cut -d' ' -f3; \
    elif [ -f ".env" ]; then \
        grep '^PYPI_TOKEN=' ".env" 2>/dev/null | cut -d'=' -f2-; \
    fi
)
endef

# Export the function to be used in the recipe
PYPI_TOKEN_FROM_FILE := $(call get_pypi_token)

# Publishing
publish: venv
	@echo "🔄 Bumping version..."
	poetry version patch
	@echo "🧹 Cleaning build artifacts..."
	@$(MAKE) clean
	@echo "🏗️  Building package..."
	poetry build
	@echo "🚀 Publishing to PyPI..."
	poetry publish
	@echo "✅ Successfully published to PyPI"

# Test publishing
TEST_PYPI_TOKEN ?= $(PYPI_TEST_TOKEN)
testpublish: build
	@if [ -z "$(TEST_PYPI_TOKEN)" ]; then \
		echo "Error: Please set PYPI_TEST_TOKEN environment variable"; \
		exit 1; \
	fi
	@echo "🚀 Publishing to TestPyPI..."
	poetry publish --build --repository testpypi --username=__token__ --password=$(TEST_PYPI_TOKEN)
	@echo "✅ Successfully published to TestPyPI"

# Try to read PyPI token from common locations
PYPI_TOKEN_FILE ?= $(shell if [ -f "${HOME}/.pypirc" ]; then echo "${HOME}/.pypirc"; elif [ -f ".pypirc" ]; then echo ".pypirc"; elif [ -f ".env" ]; then echo ".env"; fi)

# Extract PyPI token from file if not provided
ifdef PYPI_TOKEN_FILE
    ifeq ("$(PYPI_TOKEN)","")
        PYPI_TOKEN := $(shell if [ -f "$(PYPI_TOKEN_FILE)" ]; then \
            if [ "$(PYPI_TOKEN_FILE)" = "${HOME}/.pypirc" ] || [ "$(PYPI_TOKEN_FILE)" = ".pypirc" ]; then \
                grep -A 2 '\[pypi\]' "$(PYPI_TOKEN_FILE)" 2>/dev/null | grep 'token = ' | cut -d' ' -f3; \
            elif [ "$(PYPI_TOKEN_FILE)" = ".env" ]; then \
                grep '^PYPI_TOKEN=' "$(PYPI_TOKEN_FILE)" 2>/dev/null | cut -d'=' -f2-; \
            fi \
        fi)
    endif
endif

# Release a new patch version and publish
release-patch:
	@echo "🚀 Starting release process..."
	@# Bump patch version
	@echo "🔄 Bumping patch version..."
	@$(MAKE) version PART=patch
	@# Push changes and tags
	@echo "📤 Pushing changes to remote..."
	@git push --follow-tags
	@# Publish to PyPI
	@if [ -n "$(PYPI_TOKEN)" ]; then \
		echo "🔑 Found PyPI token in $(PYPI_TOKEN_FILE)"; \
		echo "🚀 Publishing to PyPI..."; \
		$(MAKE) publish; \
	else \
		echo "ℹ️  PyPI token not found. Tried: ~/.pypirc, .pypirc, .env"; \
		echo "   To publish to PyPI, either:"; \
		echo "   1. Add token to ~/.pypirc or .pypirc: [pypi]\n   token = pypi_..."; \
		echo "   2. Add PYPI_TOKEN=... to .env file"; \
		echo "   3. Run: make release-patch PYPI_TOKEN=your_token_here"; \
	fi
	@echo "✅ Release process completed!"

# Docker
docker:
	docker build -t dialogchain:latest .
	@echo "✅ Docker image built: dialogchain:latest"

docker-run: docker
	docker run -it --rm \
		-v $(PWD)/examples:/app/examples \
		-v $(PWD)/.env:/app/.env \
		dialogchain:latest \
		dialogchain run -c examples/simple.yaml

# Examples and setup
setup-env: venv
	@if [ ! -f .env ]; then \
		if [ -f .env.example ]; then \
			cp .env.example .env; \
			echo "✅ Created .env file from template"; \
		else \
			touch .env; \
			echo "✅ Created empty .env file"; \
		fi; \
		echo "📝 Please edit .env with your configuration"; \
	else \
		echo "ℹ️  .env file already exists"; \
	fi

# List available examples
list-examples:
	@echo "Available examples:"
	@echo "  make camera  - Run camera processing pipeline"
	@echo "  make mqtt    - Run MQTT example"
	@echo "  make grpc    - Run gRPC example"

# Example targets
camera: setup-env
	@echo "🚀 Running camera processing pipeline..."
	poetry run dialogchain run -c examples/camera.yaml

rtsp: setup-env
	@echo "🚀 Running camera processing pipeline..."
	poetry run dialogchain run -c examples/rtsp.yaml

mqtt: setup-env
	@echo "🚀 Starting MQTT broker and running IoT example..."
	docker-compose -f examples/docker-compose.yml up -d mosquitto
	poetry run dialogchain run -c examples/iot.yaml

grpc: setup-env
	@echo "🚀 Starting gRPC server and running example..."
	docker-compose -f examples/docker-compose.yml up -d grpc-server
	poetry run dialogchain run -c examples/grpc.yaml

# View logs for running example
view-logs:
	@if [ -z "$(EXAMPLE)" ]; then \
		echo "Error: Please specify an example with EXAMPLE=name"; \
		echo "Available examples: simple, grpc, iot, camera"; \
		exit 1; \
	fi
	@case "$(EXAMPLE)" in \
		grpc|iot) \
			docker-compose -f examples/docker-compose.yml logs -f ;; \
		*) \
			tail -f logs/dialogchain.log ;; \
	esac

# Stop a running example
stop-example:
	@if [ -z "$(EXAMPLE)" ]; then \
		echo "Error: Please specify an example with EXAMPLE=name"; \
		echo "Available examples: simple, grpc, iot, camera"; \
		exit 1; \
	fi
	@case "$(EXAMPLE)" in \
		grpc|iot) \
			docker-compose -f examples/docker-compose.yml down -v --remove-orphans ;; \
		*) \
			echo "Example '$(EXAMPLE)' runs in the foreground. Use Ctrl+C to stop." ;; \
	esac

# Stop all Docker containers and remove volumes
stop:
	@echo "Stopping all Docker containers and removing volumes..."
	@docker-compose -f examples/docker-compose.yml down -v --remove-orphans || true
	@echo "✅ All Docker containers stopped and volumes removed"

# Network Configuration
# ====================

# Default network (can be overridden)
DEFAULT_NETWORK ?= 192.168.188.0/24

# Get the default network interface
DEFAULT_IFACE := $(shell ip route | grep '^default' | awk '{print $$5}' | head -1)

# Get the current network from the default interface
CURRENT_NETWORK := $(shell ip -4 -o addr show $(DEFAULT_IFACE) 2>/dev/null | awk '{print $$4}' | cut -d'/' -f1 | sed 's/$$/\/24/')

# Network Information
network-info:
	@echo "🔍 Network Information"
	@echo "-------------------"
	@echo "Interface: $(DEFAULT_IFACE)"
	@echo "Local IP:  $(shell hostname -I | awk '{print $$1}')"
	@echo "Network:   $(CURRENT_NETWORK)"
	@echo "Gateway:   $(shell ip route | grep '^default' | awk '{print $$3}')"
	@echo "Using:     $(DEFAULT_NETWORK) (DEFAULT_NETWORK)"

# Update .env with current network settings
update-env:
	@echo "📝 Updating .env with network settings..."
	@if [ -f .env ]; then \
		sed -i "s/^DEFAULT_NETWORK=.*/DEFAULT_NETWORK=$(DEFAULT_NETWORK)/" .env; \
	else \
		echo "DEFAULT_NETWORK=$(DEFAULT_NETWORK)" > .env; \
	fi
	@echo "✅ Updated .env with DEFAULT_NETWORK=$(DEFAULT_NETWORK)"

# Get current network (for scripts)
get-network:
	@echo "$(DEFAULT_NETWORK)"

# Network Scanning
# ===============
SCAN_SCRIPT=scripts/network_scanner.py
PRINTER_SCRIPT=scripts/printer_scanner.py

# Common scanning parameters
COMMON_PORTS=80,443,554,8000-8090,8443,8554,8888,9000-9001,10000-10001
SERVICES=rtsp,http,https,onvif,rtmp,rtmps,rtmpt,rtmpts,rtmpe,rtmpte,rtmfp

# Network scanning targets
.PHONY: scan-network scan-cameras scan-camera scan-printers scan-local scan-quick scan-full scan-local-camera help

## Network scanning
scan-network: venv ## Scan the default network for common services
	@echo "🔍 Scanning $(DEFAULT_NETWORK) for common services..."
	@python3 $(SCAN_SCRIPT) --network $(DEFAULT_NETWORK) --service $(SERVICES) --port $(COMMON_PORTS)

# Network scanner settings
SCAN_PORTS := 80,81,82,83,84,85,86,87,88,89,90,443,554,8000-8100,8443,8554,8888,9000-9010,10000-10010
SCAN_SERVICES := rtsp,http,https,onvif
SCAN_TIMEOUT := 2

## Camera-specific scanning
scan-cameras: venv ## Scan for cameras and related services
	@echo "📷 Scanning for cameras (RTSP, HTTP, ONVIF, etc.)..."
	@./venv/bin/python $(SCAN_SCRIPT) --network $(DEFAULT_NETWORK) --service $(SCAN_SERVICES) --port $(SCAN_PORTS) --timeout $(SCAN_TIMEOUT) --verbose

scan-camera: venv ## Scan a specific camera IP (make scan-camera IP=192.168.1.100)
	@if [ -z "$(IP)" ]; then echo "❌ Please specify an IP address: make scan-camera IP=192.168.1.100"; exit 1; fi
	@echo "🔍 Scanning camera at $(IP)..."
	@./venv/bin/python $(SCAN_SCRIPT) --network $(IP) --service $(SCAN_SERVICES) --port $(SCAN_PORTS) --timeout $(SCAN_TIMEOUT) --verbose

## Quick and full network scans
scan-quick: venv ## Quick scan of common ports (fast but less thorough)
	@echo "⚡ Quick network scan..."
	@./venv/bin/python $(SCAN_SCRIPT) --network $(DEFAULT_NETWORK) --port 21-23,80,443,554,8000,8080,8081,8443,9000 --timeout 1

scan-full: venv ## Comprehensive scan (slower but more thorough)
	@echo "🔍 Full network scan (this may take a while)..."
	@./venv/bin/python $(SCAN_SCRIPT) --network $(DEFAULT_NETWORK) --port 1-10000 --timeout 2

## Local network scan (common home network ranges)
scan-local: venv ## Scan common local network ranges
	@echo "🏠 Scanning common local network ranges..."
	@for net in 192.168.0.0/24 192.168.1.0/24 192.168.2.0/24 10.0.0.0/24 10.0.1.0/24; do \
		echo "\n📡 Scanning network: $$net"; \
		./venv/bin/python $(SCAN_SCRIPT) --network $$net --service $(SCAN_SERVICES) --port $(SCAN_PORTS) --timeout $(SCAN_TIMEOUT); \
	done

## Printer management
scan-printers: venv ## List all available printers
	@echo "🖨️  Listing available printers..."
	@python3 $(PRINTER_SCRIPT) list

## Help target
help: ## Show this help
	@echo "\nAvailable commands:"
	@echo "================="
	@echo "Network Scanning:"
	@echo "  make scan-network    - Scan default network for common services"
	@echo "  make scan-cameras    - Scan for cameras and related services"
	@echo "  make scan-camera     - Scan a specific camera (IP=required)"
	@echo "  make scan-quick      - Quick scan of common ports"
	@echo "  make scan-full       - Comprehensive network scan (slow)"
	@echo "  make scan-local      - Scan common local network ranges"
	@echo "  make scan-local-camera - Scan local networks specifically for cameras"
	@echo "\nPrinter Management:"
	@echo "  make scan-printers   - List available printers"
	@echo "  make print-test      - Print a test page to default printer"
	@echo "\nExamples:"
	@echo "  make scan-camera IP=192.168.1.100  # Scan specific device"
	@echo "  make scan-network NETWORK=10.0.0.0/24  # Scan custom network"
	@echo "  make scan-printers  # List all available printers"

print-test:
	@echo "🖨️  Sending test page to default printer..."
	@echo "Hello from DialogChain! This is a test print." | python3 $(PRINTER_SCRIPT) print

# Advanced scanning options
scan-network-detailed:
	@echo "🔍 Detailed network scan (slower but more thorough)..."
	@python3 $(SCAN_SCRIPT) --network 192.168.1.0/24 --service rtsp,http,https,ssh,vnc

scan-custom-network:
	@echo "🔍 Scanning custom network (usage: make scan-custom-network NETWORK=192.168.0.0/24)"
	@python3 $(SCAN_SCRIPT) --network $(or $(NETWORK),192.168.1.0/24)

scan-custom-ports:
	@echo "🔍 Scanning custom ports (usage: make scan-custom-ports PORTS=80,443,8080)"
	@python3 $(SCAN_SCRIPT) --port $(or $(PORTS),80,443,8080)



run-simple: setup-env
	@echo "🚀 Running simple example..."
	@make run-example EXAMPLE=simple

validate:
	poetry run dialogchain validate -c examples/simple.yaml
	@echo "✅ Configuration validated"

dry-run:
	poetry run dialogchain run -c examples/simple.yaml --dry-run
	@echo "✅ Dry run completed"

# External processor compilation
build-go:
	@echo "🔨 Building Go processors..."
	cd scripts && go mod init dialogchain-processors || true
	cd scripts && go mod tidy || true
	cd scripts && go build -o ../bin/image_processor image_processor.go
	cd scripts && go build -o ../bin/health_check health_check.go
	@echo "✅ Go processors built in bin/"

build-cpp:
	@echo "🔨 Building C++ processors (if available)..."
	@if [ -f scripts/cpp_processor.cpp ]; then \
		mkdir -p bin; \
		g++ -O3 -o bin/cpp_postprocessor scripts/cpp_processor.cpp; \
		echo "✅ C++ processor built"; \
	else \
		echo "⚠️  No C++ processor found"; \
	fi

build-rust:
	@echo "🔨 Building Rust processors (if available)..."
	@if [ -f scripts/Cargo.toml ]; then \
		cd scripts && cargo build --release; \
		cp scripts/target/release/* bin/ 2>/dev/null || true; \
		echo "✅ Rust processors built"; \
	else \
		echo "⚠️  No Rust processor found"; \
	fi

build-all: build-go build-cpp build-rust
	@echo "✅ All external processors built"

# Monitoring and debugging
logs:
	tail -f alerts/*.log

monitor:
	@echo "📊 Starting monitoring dashboard..."
	python -c "\
import http.server\
import socketserver\
import webbrowser\
import os\
\
PORT = 8080\
Handler = http.server.SimpleHTTPRequestHandler\
\
os.chdir('monitoring')\
with socketserver.TCPServer(('', PORT), Handler) as httpd:\
    print(f'Monitoring dashboard at http://localhost:{PORT}')\
    webbrowser.open(f'http://localhost:{PORT}')\
    httpd.serve_forever()\
"

# Documentation
docs:
	@echo "📚 Generating documentation..."
	@mkdir -p docs
	@echo "import dialogchain\nhelp(dialogchain)" | python > docs/api.md
	@echo "✅ Documentation generated in docs/"

# Deployment helpers
deploy-docker:
	docker tag dialogchain:latest your-registry.com/dialogchain:latest
	docker push your-registry.com/dialogchain:latest
	@echo "✅ Docker image deployed"

deploy-k8s:
	kubectl apply -f k8s/
	@echo "✅ Deployed to Kubernetes"

# Performance testing
benchmark:
	@echo "🏃 Running performance benchmarks..."
	python scripts/benchmark.py
	@echo "✅ Benchmarks completed"

# Quick start for new users
quickstart: install-deps setup-env init-camera build-go
	@echo ""
	@echo "🎉 DialogChain Quick Start Complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit .env with your camera and email settings"
	@echo "2. Run: make run-camera"
	@echo "3. Check the logs and alerts/"
	@echo ""
	@echo "For more examples: make run-example"
	@echo "For validation: make validate"

# Development workflow
dev-workflow: dev lint test build
	@echo "✅ Development workflow completed"
## Scan for cameras on local networks
scan-local-camera: ## Scan common local networks for cameras
	@echo "🔍 Scanning local networks for cameras..."
	@for net in 192.168.0.0/24 192.168.1.0/24 192.168.2.0/24 10.0.0.0/24 10.0.1.0/24; do \
		echo "\n📡 Scanning for cameras on network: $$net"; \
		python3 $(SCAN_SCRIPT) --network $$net --service rtsp,http,https,onvif --port 80,81,82,83,84,85,86,87,88,89,90,443,554,8000-8100,8443,8554,8888,9000-9010,10000-10010 --timeout 2 --verbose; \
	done
