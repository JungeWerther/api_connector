from functools import wraps
from dataclasses import dataclass
"""Error classes and decorators for the APIConnector module."""

# custom error class for all api-connector related errors
@dataclass
class APIConnectorError(BaseException):
    """Base class for APIConnector errors."""
    message: Exception | str = None
    status: str = "error"
    code: int = 400

# add_errors decorator which takes adds a try/except block to the function, returning the error.
# allows passing an error object consisting of a code and message to the caller.

def add_error(message, code):
    """Decorator to add error handling to a function."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                raise APIConnectorError(message, code, e) from e
        return wrapper
    return decorator

class ErrorHandlingMeta(type):
    def __new__(cls, name, bases, attrs):
        for attr_name, attr_value in attrs.items():
            if callable(attr_value):
                attrs[attr_name] = add_error(f"Error executing {attr_name}", 472)(attr_value)
        return super().__new__(cls, name, bases, attrs)

class MyClass(metaclass=ErrorHandlingMeta):
    def my_method(self):
        # method implementation
        pass