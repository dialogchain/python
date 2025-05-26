"""
Network scanner module for DialogChain.
Provides functionality to scan for various network services like RTSP, SMTP, IMAP, etc.
"""
import asyncio
import ipaddress
import socket
import nmap
import cv2
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

@dataclass
class NetworkService:
    """Represents a discovered network service."""
    ip: str
    port: int
    service: str
    protocol: str = 'tcp'
    banner: Optional[str] = None
    is_secure: bool = False

class NetworkScanner:
    """Network scanner for discovering services."""
    
    COMMON_PORTS = {
        'rtsp': [554, 8554],
        'smtp': [25, 465, 587],
        'smtps': [465, 587],
        'imap': [143, 993],
        'imaps': [993],
        'http': [80, 8080, 8000, 8888],
        'https': [443, 8443],
        'rtmp': [1935],
        'rtmps': [1935],
        'ftp': [21],
        'ftps': [990],
        'ssh': [22],
        'vnc': [5900, 5901],
        'rdp': [3389],
        'mqtt': [1883],
        'mqtts': [8883],
        'grpc': [50051]
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
    
    async def scan_network(self, network: str = '192.168.1.0/24', 
                         ports: Optional[List[int]] = None,
                         service_types: Optional[List[str]] = None) -> List[NetworkService]:
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
        ports_str = ','.join(map(str, ports))
        self.nm.scan(hosts=network, ports=ports_str, arguments=f'-T4 -sS -sV --version-intensity 2')
        
        services = []
        for host in self.nm.all_hosts():
            for proto in self.nm[host].all_protocols():
                ports = self.nm[host][proto].keys()
                for port in ports:
                    port_info = self.nm[host][proto][port]
                    service = NetworkService(
                        ip=host,
                        port=port,
                        service=port_info.get('name', 'unknown'),
                        protocol=proto,
                        banner=port_info.get('product', '') + ' ' + port_info.get('version', ''),
                        is_secure=port_info.get('tunnel') == 'ssl' or 's' in port_info.get('name', '')
                    )
                    services.append(service)
        
        return services
    
    async def scan_rtsp_servers(self, network: str = '192.168.1.0/24') -> List[NetworkService]:
        """Scan for RTSP servers on the network."""
        return await self.scan_network(network, service_types=['rtsp'])
    
    async def scan_email_servers(self, network: str = '192.168.1.0/24') -> List[NetworkService]:
        """Scan for email servers (SMTP, IMAP) on the network."""
        return await self.scan_network(network, service_types=['smtp', 'smtps', 'imap', 'imaps'])
        
    async def _run_in_executor(self, func: Callable, *args) -> Any:
        """Run a function in the thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args)
    
    async def check_rtsp_stream(self, ip: str, port: int = 554, timeout: float = 2.0) -> bool:
        """Check if an RTSP stream is accessible using OpenCV."""
        rtsp_url = f"rtsp://{ip}:{port}"
        
        def _check() -> bool:
            cap = None
            try:
                cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('H', '2', '6', '4'))
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

    async def check_rtsp_stream(self, ip: str, port: int = 554, timeout: float = 2.0) -> bool:
        """Check if an RTSP stream is accessible."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=timeout
            )
            writer.write(b'OPTIONS * RTSP/1.0\r\n\r\n')
            data = await asyncio.wait_for(reader.read(1024), timeout=timeout)
            writer.close()
            await writer.wait_closed()
            return b'RTSP/1.0' in data
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
        result.append(f"{'IP':<15} {'Port':<6} {'Service':<10} {'Protocol':<8} {'Secure':<6} {'Banner'}")
        result.append("-" * 60)
        
        for svc in sorted(services, key=lambda x: (x.ip, x.port)):
            secure = 'Yes' if svc.is_secure else 'No'
            result.append(f"{svc.ip:<15} {svc.port:<6} {svc.service:<10} {svc.protocol:<8} {secure:<6} {svc.banner or ''}")
        
        return "\n".join(result)
