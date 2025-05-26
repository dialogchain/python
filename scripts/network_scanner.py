#!/usr/bin/env python3
"""
Network scanner script for DialogChain.
Provides basic network scanning capabilities without requiring root privileges.
"""

import asyncio
import socket
import aiohttp
import argparse
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

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
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError, ConnectionResetError):
            return False
    
    async def identify_service(self, ip: str, port: int) -> Dict[str, Any]:
        """Identify service running on the port."""
        # First check common ports
        for service, ports in self.COMMON_PORTS.items():
            if port in ports:
                return {
                    'service': service,
                    'protocol': 'tcp',
                    'secure': port in [443, 8443, 8883],
                    'banner': ''
                }
        
        # Try to identify web services
        if port in [80, 443, 8080, 8000, 8001, 8888, 8443]:
            is_https = port in [443, 8443]
            service = await self.check_web_service(ip, port, is_https)
            if service:
                return service
        
        return {
            'service': 'unknown',
            'protocol': 'tcp',
            'secure': False,
            'banner': ''
        }
        
    async def check_web_service(self, ip: str, port: int, is_https: bool = False) -> Optional[Dict[str, Any]]:
        """Check if a web service is running on the port."""
        protocol = 'https' if is_https else 'http'
        url = f"{protocol}://{ip}:{port}"
        
        try:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout), 
                                        ssl=False, allow_redirects=True) as response:
                        if response.status < 500:  # Any success or client error
                            return {
                                'service': 'http' if not is_https else 'https',
                                'protocol': 'tcp',
                                'secure': is_https,
                                'banner': f"HTTP {response.status} {response.reason}",
                                'headers': dict(response.headers)
                            }
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    pass
        except Exception as e:
            pass
            
        return None
    
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
        if not is_open:
            return NetworkService(ip=ip, port=port, is_up=False)
            
        service_info = await self.identify_service(ip, port)
        return NetworkService(
            ip=ip,
            port=port,
            service=service_info['service'],
            protocol=service_info['protocol'],
            banner=service_info.get('banner', ''),
            is_secure=service_info.get('secure', False),
            is_up=True
        )

async def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='Network scanner for DialogChain')
    parser.add_argument('--network', '-n', default='192.168.1.0/24',
                      help='Network to scan in CIDR notation (default: 192.168.1.0/24)')
    parser.add_argument('--service', '-s', action='append',
                      help='Service types to scan (rtsp, http, https, ssh, etc.)')
    parser.add_argument('--port', '-p', default=None,
                      help='Comma-separated list of ports or port ranges to scan (e.g., 80,443,8000-9000)')
    parser.add_argument('--timeout', '-t', type=float, default=3.0,
                      help='Connection timeout in seconds (default: 3.0)')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Show detailed output')
    
    args = parser.parse_args()
    
    # Process ports from --port argument
    ports = []
    if args.port:
        for port_str in args.port.split(','):
            port_str = port_str.strip()
            if '-' in port_str:
                # Handle port ranges (e.g., 8000-9000)
                try:
                    start, end = map(int, port_str.split('-'))
                    ports.extend(range(start, end + 1))
                except (ValueError, IndexError):
                    print(f"Warning: Invalid port range '{port_str}'. Skipping...")
            elif port_str.isdigit():
                ports.append(int(port_str))
    
    scanner = SimpleNetworkScanner(timeout=args.timeout)
    
    if args.verbose:
        print(f"Starting network scan on {args.network}")
        if ports:
            print(f"Scanning ports: {', '.join(map(str, ports))}")
        if args.service:
            print(f"Scanning services: {', '.join(args.service)}")
    
    try:
        services = await scanner.scan_network(
            network=args.network,
            ports=ports if ports else None,
            service_types=args.service
        )
        
        # Filter only active services
        active_services = [s for s in services if s.is_up]
        
        if args.verbose or not active_services:
            print("\nScan Results:")
            print("-" * 60)
            print(f"{'IP':<15} {'Port':<6} {'Service':<10} {'Status'}")
            print("-" * 60)
        
        if not active_services:
            print("No active services found.")
            if not args.verbose:
                print("Use -v for more detailed output.")
            return
        
        for svc in sorted(active_services, key=lambda x: (x.ip, x.port)):
            status = "UP"
            print(f"{svc.ip:<15} {svc.port:<6} {svc.service:<10} {status}")
            
    except KeyboardInterrupt:
        print("\nScan interrupted by user.")
    except Exception as e:
        print(f"\nError during scan: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    asyncio.run(main())
