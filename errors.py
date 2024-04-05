# custom error class for all api-connector related errors
class APIConnectorError(BaseException):
    """Base class for APIConnector errors."""
    message: str = None
    code: int = "400"
    error: Exception = None

# add_errors decorator which takes adds a try/except block to the function, returning the error.
# allows passing an error object consisting of a code and message to the caller.

def add_error(message, code):
    """Decorator to add error handling to a function."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                raise APIConnectorError(message, code, e) from e
        return wrapper
    return decorator
