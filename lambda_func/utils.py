import json, os, time, random, boto3
from decimal import Decimal
from botocore.exceptions import ClientError
from enum import Enum


class APIError(Exception):
    """Base exception for predictable API errors."""
    def __init__(self, message, status_code=400, error_code="BAD_REQUEST"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code

class ValidationError(APIError):
    """Raised when input validation fails."""
    def __init__(self, message, errors=None):
        super().__init__(message, status_code=422, error_code="VALIDATION_ERROR")
        self.errors = errors or {}

class TransientError(APIError):
    """Raised for temporary infrastructure or database issues eligible for retry."""
    def __init__(self, message="Temporary service disruption. Please retry."):
        super().__init__(message, status_code=503, error_code="TRANSIENT_ERROR")

def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def create_response(status_code, body=None):
    """Format API Gateway responses with the deployment's explicit web origin."""
    allowed_origin = os.environ.get("ALLOWED_ORIGIN")
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Methods": "GET, POST, PUT, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Vary": "Origin",
    }
    if allowed_origin:
        headers["Access-Control-Allow-Origin"] = allowed_origin
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body, default=decimal_serializer) if body is not None else ""
    }

def create_error_response(error):
    """Formats standardized error response payloads for clients."""
    if isinstance(error, ValidationError):
        body = {
            "error": error.error_code,
            "message": error.message,
            "details": error.errors
        }
        return create_response(error.status_code, body)
    
    if isinstance(error, APIError):
        body = {
            "error": error.error_code,
            "message": error.message
        }
        return create_response(error.status_code, body)
    
    return create_response(500, {
        "error": "INTERNAL_SERVER_ERROR",
        "message": "An unexpected error occurred. Please try again later."
    })

# Reusable retry decorator for transient AWS errors
def retry_on_transient_error(max_attempts=3, base_delay=0.5):
    """Decorator to retry operations on transient AWS failures with exponential backoff."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except ClientError as e:
                    error_code = e.response["Error"]["Code"]
                    # List of AWS transient/throttle error codes eligible for retry
                    transient_codes = [
                        "ProvisionedThroughputExceededException",
                        "RequestLimitExceeded",
                        "InternalServerError",
                        "ServiceUnavailable"
                    ]
                    if error_code in transient_codes:
                        attempts += 1
                        if attempts == max_attempts:
                            raise TransientError(f"Operation failed after {max_attempts} retries due to temporary service issues.")
                        # Exponential backoff with jitter
                        exponential_delay = base_delay * (2 ** (attempts - 1))
                        wait_time = (exponential_delay / 2) + random.uniform(0, exponential_delay / 2)
                        time.sleep(wait_time)
                    else:
                        raise
        return wrapper
    return decorator

# Reusable circuit breaker implementation for external service calls
class CircuitBreakerOpenException(APIError):
    def __init__(self, message="Service temporarily unavailable due to high error rates. Circuit is OPEN."):
        super().__init__(message, status_code=503, error_code="CIRCUIT_BREAKER_OPEN")

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=30, success_threshold=2):
        self.failure_threshold = failure_threshold  # Failures before opening
        self.timeout = timeout  # Seconds before trying half-open
        self.success_threshold = success_threshold  # Successes to close circuit
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func, *args, **kwargs):
        # Check if circuit should move to half-open
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise CircuitBreakerOpenException("Circuit is OPEN. Please try again later.")
        
        try:
            # Attempt the call
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        self.failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# # Usage in payment processing
# payment_circuit = CircuitBreaker(failure_threshold=5, timeout=30)

# def process_payment(order_id, amount):
#     try:
#         result = payment_circuit.call(payment_gateway.charge, amount=amount)
#         return {"status": "success", "transaction_id": result.id}
#     except Exception as e:
#         # Circuit is open or payment failed
#         return {"status": "failed", "error": str(e)}