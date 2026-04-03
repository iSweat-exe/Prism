from typing import Optional


class PrismError(Exception):
    """Base exception for all PrismAPI related errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "internal_server_error",
        status_code: int = 500,
        details: Optional[dict] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class DockerServiceError(PrismError):
    """Exception raised when Docker operations fail."""

    def __init__(self, message: str, status_code: int = 503, details: Optional[dict] = None):
        super().__init__(message, error_code="docker_service_error", status_code=status_code, details=details)


class PM2ServiceError(PrismError):
    """Exception raised when PM2 operations fail."""

    def __init__(self, message: str, status_code: int = 503, details: Optional[dict] = None):
        super().__init__(message, error_code="pm2_service_error", status_code=status_code, details=details)


class ResourceNotFoundError(PrismError):
    """Exception raised when a requested resource (container, process, etc.) is not found."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, error_code="not_found", status_code=404, details=details)


class ValidationError(PrismError):
    """Exception raised for input validation errors."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, error_code="validation_error", status_code=422, details=details)
