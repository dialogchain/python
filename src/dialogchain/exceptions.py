"""
Custom exceptions for Camel Router
"""


class CamelRouterError(Exception):
    """Base exception for Camel Router"""

    pass


class ConfigurationError(CamelRouterError):
    """Configuration related errors"""

    pass


class ProcessorError(CamelRouterError):
    """Processor execution errors"""

    pass


class ConnectorError(CamelRouterError):
    """Connector related errors"""

    pass


class ValidationError(CamelRouterError):
    """Validation errors"""

    pass


class TimeoutError(CamelRouterError):
    """Timeout errors"""

    pass


class ScannerError(CamelRouterError):
    """Scanner related errors"""
    
    pass


class ExternalProcessError(ProcessorError):
    """External process execution errors"""

    def __init__(self, message: str, return_code: int = None, stderr: str = None):
        super().__init__(message)
        self.return_code = return_code
        self.stderr = stderr


class SourceConnectionError(ConnectorError):
    """Source connection errors"""

    pass


class DestinationError(ConnectorError):
    """Destination errors"""

    pass
