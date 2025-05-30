"""
Scanner module for DialogChain.
Provides functionality to scan for configuration files from various sources.
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, AsyncGenerator
from urllib.parse import urlparse
import aiohttp
from dataclasses import dataclass
import aiofiles

logger = logging.getLogger(__name__)

class ScannerError(Exception):
    """Base exception for scanner related errors."""
    pass

class BaseScanner:
    """Base class for all scanners."""
    
    async def scan(self) -> List[str]:
        """Scan for configuration files.
        
        Returns:
            List of configuration file paths or URLs
        """
        raise NotImplementedError("Subclasses must implement scan()")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class FileScanner(BaseScanner):
    """Scanner for local file system configurations."""
    
    def __init__(self, path: str, pattern: str = "*.yaml", recursive: bool = True):
        """Initialize file scanner.
        
        Args:
            path: Base directory to scan
            pattern: File pattern to match (e.g., '*.yaml')
            recursive: Whether to scan subdirectories
        """
        self.path = Path(path).expanduser().resolve()
        self.pattern = pattern
        self.recursive = recursive
    
    async def scan(self) -> List[str]:
        """Scan for configuration files.
        
        Returns:
            List of absolute file paths
        """
        if not self.path.exists():
            raise ScannerError(f"Path does not exist: {self.path}")
        
        if not self.path.is_dir():
            return [str(self.path)] if self.path.suffix in ('.yaml', '.yml') else []
        
        result = []
        if self.recursive:
            for file_path in self.path.rglob(self.pattern):
                if file_path.is_file():
                    result.append(str(file_path))
        else:
            for file_path in self.path.glob(self.pattern):
                if file_path.is_file():
                    result.append(str(file_path))
        
        return result


class HttpScanner(BaseScanner):
    """Scanner for HTTP/HTTPS configuration endpoints."""
    
    def __init__(self, url: str, timeout: int = 30):
        """Initialize HTTP scanner.
        
        Args:
            url: Base URL to scan
            timeout: Request timeout in seconds
        """
        self.url = url
        self.timeout = aiohttp.ClientTimeout(total=timeout)
    
    async def scan(self) -> List[str]:
        """Scan HTTP endpoint for configurations.
        
        Returns:
            List of configuration URLs
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.url) as response:
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '')
                        if 'yaml' in content_type or 'yml' in content_type:
                            return [self.url]
                        # TODO: Handle directory listings or API responses
                        return [self.url]
                    response.raise_for_status()
                    return []
        except aiohttp.ClientError as e:
            raise ScannerError(f"HTTP request failed: {e}")


def create_scanner(config: Dict[str, Any]) -> BaseScanner:
    """Create a scanner instance based on configuration.
    
    Args:
        config: Scanner configuration
        
    Returns:
        Scanner instance
        
    Raises:
        ValueError: If scanner type is unknown
    """
    scanner_type = config.get('type')
    
    if scanner_type == 'file':
        return FileScanner(
            path=config['path'],
            pattern=config.get('pattern', '*.yaml'),
            recursive=config.get('recursive', True)
        )
    elif scanner_type == 'http':
        return HttpScanner(
            url=config['url'],
            timeout=config.get('timeout', 30)
        )
    else:
        raise ValueError(f"Unknown scanner type: {scanner_type}")


class ConfigScanner:
    """Manages multiple scanners and aggregates their results."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize config scanner.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.scanners = []
        
        # Create scanners from config
        for scanner_config in config.get('scanners', []):
            try:
                scanner = create_scanner(scanner_config)
                self.scanners.append(scanner)
            except Exception as e:
                logger.warning(f"Failed to create scanner: {e}")
    
    async def scan(self) -> List[str]:
        """Run all scanners and collect results.
        
        Returns:
            List of configuration file paths/URLs
            
        Raises:
            ScannerError: If scanning fails
        """
        results = set()
        
        for scanner in self.scanners:
            try:
                scanner_results = await scanner.scan()
                results.update(scanner_results)
            except Exception as e:
                raise ScannerError(f"Scanner failed: {e}") from e
        
        return list(results)


@dataclass
class NetworkService:
    """Represents a discovered network service."""

    ip: str
    port: int
    service: str
    protocol: str = "tcp"
    banner: Optional[str] = None
    is_secure: bool = False


class NetworkScanner:
    """Network scanner for discovering services."""

    COMMON_PORTS = {
        "rtsp": [554, 8554],
        "smtp": [25, 465, 587],
        "smtps": [465, 587],
        "imap": [143, 993],
        "imaps": [993],
        "http": [80, 8080, 8000, 8888],
        "https": [443, 8443],
        "rtmp": [1935],
        "rtmps": [1935],
        "ftp": [21],
        "ftps": [990],
        "ssh": [22],
        "vnc": [5900, 5901],
        "rdp": [3389],
        "mqtt": [1883],
        "mqtts": [8883],
        "grpc": [50051],
    }

    def __init__(self, timeout: float = 2.0, max_workers: int = 50):
        """Initialize the network scanner.

        Args:
            timeout: Timeout in seconds for each connection attempt
            max_workers: Maximum number of concurrent scans
        """
        self.timeout = timeout
        self.max_workers = max_workers
        self.nm = nmap.PortScanner()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def scan_network(
        self,
        network: str = "192.168.1.0/24",
        ports: Optional[List[int]] = None,
        service_types: Optional[List[str]] = None,
    ) -> List[NetworkService]:
        """Scan a network for common services.

        Args:
            network: Network CIDR notation (e.g., '192.168.1.0/24')
            ports: List of ports to scan (if None, scans common ports)
            service_types: List of service types to scan (e.g., ['rtsp', 'smtp'])

        Returns:
            List of discovered NetworkService objects
        """
        if ports is None and service_types is None:
            ports = list(set(p for ports in self.COMMON_PORTS.values() for p in ports))
        elif service_types:
            ports = []
            for svc in service_types:
                if svc in self.COMMON_PORTS:
                    ports.extend(self.COMMON_PORTS[svc])
            ports = list(set(ports))

        # Use nmap for initial port scanning
        ports_str = ",".join(map(str, ports))
        self.nm.scan(
            hosts=network,
            ports=ports_str,
            arguments=f"-T4 -sS -sV --version-intensity 2",
        )

        services = []
        for host in self.nm.all_hosts():
            for proto in self.nm[host].all_protocols():
                ports = self.nm[host][proto].keys()
                for port in ports:
                    port_info = self.nm[host][proto][port]
                    service = NetworkService(
                        ip=host,
                        port=port,
                        service=port_info.get("name", "unknown"),
                        protocol=proto,
                        banner=port_info.get("product", "")
                        + " "
                        + port_info.get("version", ""),
                        is_secure=port_info.get("tunnel") == "ssl"
                        or "s" in port_info.get("name", ""),
                    )
                    services.append(service)

        return services

    async def scan_rtsp_servers(
        self, network: str = "192.168.1.0/24"
    ) -> List[NetworkService]:
        """Scan for RTSP servers on the network."""
        return await self.scan_network(network, service_types=["rtsp"])

    async def scan_email_servers(
        self, network: str = "192.168.1.0/24"
    ) -> List[NetworkService]:
        """Scan for email servers (SMTP, IMAP) on the network."""
        return await self.scan_network(
            network, service_types=["smtp", "smtps", "imap", "imaps"]
        )

    async def _run_in_executor(self, func: Callable, *args) -> Any:
        """Run a function in the thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args)

    async def check_rtsp_stream(
        self, ip: str, port: int = 554, timeout: float = 2.0
    ) -> bool:
        """Check if an RTSP stream is accessible using OpenCV."""
        rtsp_url = f"rtsp://{ip}:{port}"

        def _check() -> bool:
            cap = None
            try:
                cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("H", "2", "6", "4"))
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, int(timeout * 1000))
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, int(timeout * 1000))
                return cap.isOpened() and cap.grab()
            except Exception:
                return False
            finally:
                if cap is not None:
                    cap.release()

        try:
            return await self._run_in_executor(_check)
        except Exception:
            return False

    async def check_rtsp_stream(
        self, ip: str, port: int = 554, timeout: float = 2.0
    ) -> bool:
        """Check if an RTSP stream is accessible."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port), timeout=timeout
            )
            writer.write(b"OPTIONS * RTSP/1.0\r\n\r\n")
            data = await asyncio.wait_for(reader.read(1024), timeout=timeout)
            writer.close()
            await writer.wait_closed()
            return b"RTSP/1.0" in data
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return False

    @staticmethod
    def format_service_list(services: List[NetworkService]) -> str:
        """Format a list of services for display."""
        if not services:
            return "No services found."

        result = []
        result.append(f"Found {len(services)} services:")
        result.append("-" * 60)
        result.append(
            f"{'IP':<15} {'Port':<6} {'Service':<10} {'Protocol':<8} {'Secure':<6} {'Banner'}"
        )
        result.append("-" * 60)

        for svc in sorted(services, key=lambda x: (x.ip, x.port)):
            secure = "Yes" if svc.is_secure else "No"
            result.append(
                f"{svc.ip:<15} {svc.port:<6} {svc.service:<10} {svc.protocol:<8} {secure:<6} {svc.banner or ''}"
            )

        return "\n".join(result)
