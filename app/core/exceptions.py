"""
Custom Application Exceptions.
Provides clear semantic failure types across tools, agents, RAG, and services.
"""


class AppBaseException(Exception):
    """Base class for all application exceptions."""
    def __init__(self, message: str, error_code: str = "INTERNAL_ERROR", details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class OrderNotFoundError(AppBaseException):
    """Raised when an order does not exist."""
    def __init__(self, order_id: str):
        super().__init__(
            message=f"Order '{order_id}' was not found in the restaurant operational system.",
            error_code="ORDER_NOT_FOUND",
            details={"order_id": order_id}
        )


class ServiceUnavailableError(AppBaseException):
    """Raised when an external or mock API service is unreachable."""
    def __init__(self, service_name: str, message: str = None):
        super().__init__(
            message=message or f"The operational service '{service_name}' is currently unavailable. Please try again shortly.",
            error_code="SERVICE_UNAVAILABLE",
            details={"service_name": service_name}
        )


class ToolExecutionError(AppBaseException):
    """Raised when an agent tool fails during execution."""
    def __init__(self, tool_name: str, message: str, details: dict = None):
        super().__init__(
            message=f"Tool '{tool_name}' execution failed: {message}",
            error_code="TOOL_EXECUTION_ERROR",
            details=details or {"tool_name": tool_name}
        )


class SecurityViolationError(AppBaseException):
    """Raised when prompt injection, unauthorized data access, or forbidden commands are detected."""
    def __init__(self, reason: str, detected_pattern: str = None):
        super().__init__(
            message=f"Security violation detected: {reason}",
            error_code="SECURITY_VIOLATION",
            details={"reason": reason, "detected_pattern": detected_pattern}
        )


class RAGRetrievalError(AppBaseException):
    """Raised when knowledge base retrieval fails."""
    def __init__(self, query: str, reason: str):
        super().__init__(
            message=f"RAG retrieval failed for query '{query}': {reason}",
            error_code="RAG_RETRIEVAL_ERROR",
            details={"query": query, "reason": reason}
        )


class LLMServiceError(AppBaseException):
    """Raised when LLM API encounters rate limits, connection drops, or invalid output."""
    def __init__(self, provider: str, message: str):
        super().__init__(
            message=f"LLM provider '{provider}' error: {message}",
            error_code="LLM_SERVICE_ERROR",
            details={"provider": provider}
        )
