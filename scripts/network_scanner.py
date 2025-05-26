#!/usr/bin/env python3
"""
Network scanner script for DialogChain.
Provides basic network scanning capabilities without requiring root privileges.
"""

import asyncio
import socket
import argparse
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class NetworkService:
    """Represents a discovered network service."""
    ip: str
    port: int
    service: str = "unknown"
    protocol: str = "tcp"
    banner: str = ""
    is_secure: bool = False
    is_up: bool = True

class SimpleNetworkScanner:
    """Simple network scanner that doesn't require root privileges."""
    
    COMMON_PORTS = {
        'rtsp': [554, 8554],
        'http': [80, 8080, 8000, 8888],
        'https': [443, 8443],
        'ssh': [22],
        'vnc': [5900, 5901],
        'rdp': [3389],
        'mqtt': [1883],
        'mqtts': [8883]
    }
    
    def __init__(self, timeout: float = 2.0):
        """Initialize the scanner with connection timeout."""
        self.timeout = timeout
    
    async def check_port(self, ip: str, port: int) -> bool:
        """Check if a port is open."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=self.timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return False
    
    def identify_service(self, port: int) -> str:
        """Identify service based on port number."""
        for service, ports in self.COMMON_PORTS.items():
            if port in ports:
                return service
        return "unknown"
    
    async def scan_network(
        self, 
        network: str = '192.168.1.0/24',
        ports: Optional[List[int]] = None,
        service_types: Optional[List[str]] = None
    ) -> List[NetworkService]:
        """Scan a network for open ports and services."""
        if ports is None and service_types is None:
            ports = list(set(p for ports in self.COMMON_PORTS.values() for p in ports))
        elif service_types:
            ports = []
            for svc in service_types:
                if svc in self.COMMON_PORTS:
                    ports.extend(self.COMMON_PORTS[svc])
            ports = list(set(ports))
        
        # Get IPs to scan
        base_ip = ".".join(network.split(".")[:3])
        ips = [f"{base_ip}.{i}" for i in range(1, 255)]
        
        # Scan ports for each IP
        tasks = []
        for ip in ips:
            for port in ports:
                tasks.append(self.scan_port(ip, port))
        
        # Run all scans concurrently
        results = await asyncio.gather(*tasks)
        return [service for service in results if service.is_up]
    
    async def scan_port(self, ip: str, port: int) -> NetworkService:
        """Scan a single port and return service info."""
        is_open = await self.check_port(ip, port)
        service = self.identify_service(port)
        return NetworkService(
            ip=ip,
            port=port,
            service=service,
            is_up=is_open
        )

async def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='Network scanner for DialogChain')
    parser.add_argument('--network', '-n', default='192.168.1.0/24',
                      help='Network to scan in CIDR notation')
    parser.add_argument('--service', '-s', action='append',
                      help='Service types to scan (rtsp, http, etc.)')
    parser.add_argument('--port', '-p', type=int, action='append',
                      help='Specific ports to scan')
    parser.add_argument('--timeout', '-t', type=float, default=1.0,
                      help='Connection timeout in seconds')
    
    args = parser.parse_args()
    
    scanner = SimpleNetworkScanner(timeout=args.timeout)
    services = await scanner.scan_network(
        network=args.network,
        ports=args.port,
        service_types=args.service
    )
    
    # Print results
    print("\nScan Results:")
    print("-" * 60)
    print(f"{'IP':<15} {'Port':<6} {'Service':<10} {'Status'}")
    print("-" * 60)
    
    for svc in sorted(services, key=lambda x: (x.ip, x.port)):
        status = "UP" if svc.is_up else "DOWN"
        print(f"{svc.ip:<15} {svc.port:<6} {svc.service:<10} {status}")

if __name__ == "__main__":
    asyncio.run(main())
