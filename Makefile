# DialogChain - Flexible Dialog Processing Framework
# Makefile for development and deployment

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
	@echo "  view-logs        - View logs for running example"
	@echo "  stop-example     - Stop a running example"
	@echo "  docs             - Generate documentation"
	@echo "  setup-env        - Create example .env file"

# Installation
install:
	pip install -e .
	pip install python-nmap opencv-python pycups
	@echo "✅ DialogChain installed"

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
test:
	pytest tests/ -v
	@echo "✅ Tests completed"

lint:
	python -m flake8 src/dialogchain/
	python -m black --check src/dialogchain/
	@echo "✅ Linting completed"

format:
	python -m black src/dialogchain/
	@echo "✅ Code formatted"

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
publish:
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
		dialogchain run -c examples/simple_routes.yaml

# Examples and setup
setup-env:
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
	@echo "  simple  - Basic routing example"
	@echo "  grpc    - gRPC service integration"
	@echo "  iot     - IoT device communication"
	@echo "  camera  - Video processing pipeline"

# Initialize example configurations
init-camera:
	poetry run dialogchain init --template camera --output examples/camera_routes.yaml
	@echo "✅ Camera configuration template created"

init-grpc:
	poetry run dialogchain init --template grpc --output examples/grpc_routes.yaml
	@echo "✅ gRPC configuration template created"

init-iot:
	poetry run dialogchain init --template iot --output examples/iot_routes.yaml
	@echo "✅ IoT configuration template created"

# Run examples
run-example: setup-env
	@if [ -z "$(EXAMPLE)" ]; then \
		echo "Error: Please specify an example with EXAMPLE=name"; \
		echo "Available examples: simple, grpc, iot, camera"; \
		exit 1; \
	fi
	@echo "🚀 Starting $(EXAMPLE) example..."
	@case "$(EXAMPLE)" in \
		simple) \
			poetry run dialogchain run -c examples/simple_config.yaml ;; \
		grpc) \
			docker-compose -f examples/docker-compose.yml up -d grpc-server && \
			poetry run dialogchain run -c examples/grpc_routes.yaml ;; \
		iot) \
			docker-compose -f examples/docker-compose.yml up -d mosquitto && \
			poetry run dialogchain run -c examples/iot_routes.yaml ;; \
		camera) \
			poetry run dialogchain run -c examples/camera_routes.yaml ;; \
		*) \
			echo "Error: Unknown example '$(EXAMPLE)'"; \
			exit 1 ;; \
	esac

# Run the simple example with verbose output
run-simple-verbose:
	poetry run dialogchain run -c examples/simple_config.yaml --verbose

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

# Alias for backward compatibility
run-camera: setup-env
	@echo "🚀 Running camera processing pipeline..."
	@make run-example EXAMPLE=camera

run-grpc: setup-env
	@echo "🚀 Running gRPC example..."
	@make run-example EXAMPLE=grpc

run-iot: setup-env
	@echo "🚀 Running IoT example..."
	@make run-example EXAMPLE=iot

scan-network:
	@echo "🔍 Scanning network for devices..."
	@python -c "from dialogchain.scanner import NetworkScanner; import asyncio; \
	    scanner = NetworkScanner(); \
	    services = asyncio.run(scanner.scan_network()); \
	    print('\n'.join(f'{s.ip}:{s.port} - {s.service} ({s.banner})' for s in services))"

scan-cameras:
	@echo "📷 Scanning for cameras..."
	@python -c "from dialogchain.scanner import NetworkScanner; import asyncio; \
	    scanner = NetworkScanner(); \
	    services = asyncio.run(scanner.scan_network(service_types=['rtsp'])); \
	    print('\n'.join(f'Camera found at rtsp://{s.ip}:{s.port}' for s in services))"

scan-printers:
	@echo "🖨️  Scanning for printers..."
	@python -c "import cups; conn = cups.Connection(); \
	    printers = conn.getPrinters(); \
	    [print(f'Printer: {p} - {printers[p]["device-uri"]}') for p in printers]"

print-test:
	@echo "🖨️  Sending test page to default printer..."
	@python -c "import cups; conn = cups.Connection(); \
	    printers = conn.getPrinters(); \
	    if printers: \
	        printer = list(printers.keys())[0]; \
	        job_id = conn.printFile(printer, '/dev/stdin', 'Test Print', {'raw': 'True'}); \
	        print(f'✅ Sent test page to {printer} (Job ID: {job_id})'); \
	    else: \
	        print('❌ No printers found')" < <(echo 'Hello from DialogChain! This is a test print.')

run-simple: setup-env
	@echo "🚀 Running simple example..."
	@make run-example EXAMPLE=simple

validate:
	poetry run dialogchain validate -c examples/simple_routes.yaml
	@echo "✅ Configuration validated"

dry-run:
	poetry run dialogchain run -c examples/simple_routes.yaml --dry-run
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