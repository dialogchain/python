"""
Network scanner for DialogChain.
Scans the network for services and configurations.
"""

import asyncio
import logging
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set, Callable, Union

import nmap

from .base import BaseScanner, ScannerError

logger = logging.getLogger(__name__)

@dataclass
class NetworkService:
    """Represents a discovered network service."""
    ip: str
    port: int
    service: str
    protocol: str = "tcp"
    banner: Optional[str] = None
    is_secure: bool = False

class NetworkScanner(BaseScanner):
    """Network scanner for discovering services."""
    
    # Common ports for various services
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
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'NetworkScanner':
        """Create a network scanner from configuration.
        
        Args:
            config: Scanner configuration dictionary
            
        Returns:
            Configured NetworkScanner instance
        """
        return cls(
            timeout=float(config.get('timeout', 2.0)),
            max_workers=int(config.get('max_workers', 50))
        )
    
    async def scan(self) -> List[str]:
        """Scan the network for services.
        
        Note: This is a placeholder implementation. In a real-world scenario,
        you would implement actual network scanning logic here.
        
        Returns:
            List of discovered service URLs
        """
        # Default implementation returns an empty list
        # You would typically implement actual network scanning here
        return []
    
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
        if ports is None:
            if service_types is None:
                service_types = list(self.COMMON_PORTS.keys())
            
            # Get all unique ports for the requested service types
            ports_set = set()
            for service in service_types:
                if service in self.COMMON_PORTS:
                    ports_set.update(self.COMMON_PORTS[service])
            
            if not ports_set:
                logger.warning(f"No known ports for service types: {service_types}")
                return []
                
            ports = sorted(ports_set)
        
        # Convert ports to nmap format (e.g., "80,443,8080")
        port_str = ",".join(str(p) for p in ports)
        
        try:
            # Run the scan
            logger.info(f"Scanning {network} on ports: {port_str}")
            scan_result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.nm.scan(
                    hosts=network,
                    ports=port_str,
                    arguments=f'-sS -T4 --min-rate=1000 --max-retries=1 --host-timeout={self.timeout}s',
                    sudo=True
                )
            )
            
            # Process results
            services = []
            for ip, host in scan_result['scan'].items():
                if 'tcp' in host:
                    for port, port_info in host['tcp'].items():
                        if port_info['state'] == 'open':
                            service = NetworkService(
                                ip=ip,
                                port=port,
                                service=port_info.get('name', 'unknown'),
                                banner=port_info.get('product', '') + ' ' + port_info.get('version', '')
                            )
                            services.append(service)
            
            return services
            
        except Exception as e:
            raise ScannerError(f"Network scan failed: {e}") from e
    
    async def scan_rtsp_servers(
        self, network: str = "192.168.1.0/24"
    ) -> List[NetworkService]:
        """Scan for RTSP servers on the network."""
        return await self.scan_network(network, service_types=["rtsp"])
    
    async def scan_email_servers(
        self, network: str = "192.168.1.0/24"
    ) -> List[NetworkService]:
        """Scan for email servers (SMTP, IMAP) on the network."""
        return await self.scan_network(network, service_types=["smtp", "imap"])
    
    def _run_in_executor(self, func: Callable, *args):
        """Run a function in the thread pool."""
        return asyncio.get_event_loop().run_in_executor(self.executor, func, *args)
    
    async def check_rtsp_stream(
        self, ip: str, port: int = 554, timeout: float = 2.0
    ) -> bool:
        """Check if an RTSP stream is accessible."""
        try:
            # Try to connect to the RTSP port
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=timeout
            )
            
            # Send OPTIONS request
            writer.write(b"OPTIONS rtsp://%s:%d/ RTSP/1.0\r\n" % (ip.encode(), port))
            writer.write(b"CSeq: 1\r\n")
            writer.write(b"\r\n")
            await writer.drain()
            
            # Read response
            data = await asyncio.wait_for(reader.read(1024), timeout=timeout)
            
            # Check if it looks like an RTSP server
            return b"RTSP/1.0" in data
            
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return False
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except (UnboundLocalError, AttributeError):
                pass
    
    @staticmethod
    def format_service_list(services: List[NetworkService]) -> str:
        """Format a list of services for display."""
        if not services:
            return "No services found"
            
        lines = ["Discovered services:", "-" * 40]
        for svc in services:
            lines.append(f"{svc.ip}:{svc.port} - {svc.service} ({svc.protocol})")
            if svc.banner:
                lines.append(f"  Banner: {svc.banner}")
            lines.append("")
            
        return "\n".join(lines)
