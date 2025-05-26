# DialogChain Scripts: Network Scanning

## Overview

This directory contains scripts for network and printer discovery in DialogChain. The main script for network scanning is `network_scanner.py`, which can detect devices and camera services (RTSP, HTTP, ONVIF, etc.) on your network.

---

## Requirements

- Python 3.8+
- Install dependencies:
  ```bash
  pip install -r ../../requirements.txt
  # or for direct script use:
  pip install aiohttp python-nmap opencv-python
  ```

---

## Usage: network_scanner.py

Scan your network for devices and services:

```bash
python3 network_scanner.py --network 192.168.1.0/24
```

Scan for cameras (RTSP, HTTP, ONVIF):

```bash
python3 network_scanner.py --network 192.168.1.0/24 --service rtsp,http,https,onvif --port 80,443,554,8000-8090,8443,8554,8888,9000-9001,10000-10001 --verbose
```

Scan a specific device:

```bash
python3 network_scanner.py --network 192.168.188.176 --service rtsp,http,https,onvif --port 80,443,554,8000,8080,8443,8554,8888
```

---

## Makefile Shortcuts

Use the Makefile in the parent directory for common scans:

- **Scan default network:**
  ```bash
  make scan-network
  ```
- **Scan for cameras:**
  ```bash
  make scan-cameras
  ```
- **Scan a specific camera:**
  ```bash
  make scan-camera IP=192.168.188.176
  ```
- **Scan common local ranges for cameras:**
  ```bash
  make scan-local-camera
  ```
- **Quick scan:**
  ```bash
  make scan-quick
  ```
- **Full scan (slow):**
  ```bash
  make scan-full
  ```

---

## Command-Line Options

- `--network`  Network or IP to scan (e.g., `192.168.1.0/24` or `192.168.1.101`)
- `--service`  Comma-separated list of services (e.g., `rtsp,http,https,onvif`)
- `--port`     Ports or port ranges (e.g., `80,443,554,8000-8090`)
- `--timeout`  Timeout per connection (default: 3.0)
- `--verbose`  Show detailed output

---

## Example: Scan for Cameras on All Local Networks

```bash
make scan-local-camera
```

This will scan all common local networks for camera-related services and print a summary of detected devices.

---

## Troubleshooting

- Ensure your Python environment has all required dependencies (`aiohttp`, etc.).
- Run scans with `--verbose` for more details.
- If no devices are found, check your network, firewall, and device connectivity.

---

For more information, see the main project README or contact the project maintainers.
