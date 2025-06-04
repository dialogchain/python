"""
Custom exceptions for DialogChain
"""


class DialogChainException(Exception):
    """Base exception for DialogChain"""
    def __init__(self, message: str, return_code: int = 1, **kwargs):
        self.return_code = return_code
        self.message = message
        self.kwargs = kwargs
        super().__init__(message)

    def __str__(self):
        return self.message


class DialogChainError(DialogChainException):
    """Base error class for DialogChain"""
    pass


class ConfigurationError(DialogChainError):
    """Configuration related errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, return_code=2, **kwargs)


class ValidationError(DialogChainError):
    """Validation errors"""
    def __init__(self, message: str, field: str = None, **kwargs):
        self.field = field
        super().__init__(message, return_code=3, **kwargs)


class ConnectorError(DialogChainError):
    """Connector related errors"""
    def __init__(self, message: str, status_code: int = None, **kwargs):
        self.status_code = status_code
        super().__init__(message, return_code=4, **kwargs)


class ProcessorError(DialogChainError):
    """Processor execution errors"""
    def __init__(self, message: str, processor_name: str = None, **kwargs):
        self.processor_name = processor_name
        super().__init__(message, return_code=5, **kwargs)


class TimeoutError(DialogChainError):
    """Timeout errors"""
    def __init__(self, message: str, timeout: float = None, **kwargs):
        self.timeout = timeout
        super().__init__(message, return_code=6, **kwargs)


class ScannerError(DialogChainError):
    """Scanner related errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, return_code=7, **kwargs)


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
