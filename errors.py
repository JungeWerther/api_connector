import json

# custom error class for all api-connector related errors
class APIConnectorError(BaseException):
    message: str = None
    code: int = "400"
    error: Exception = None

# add_errors decorator which takes adds a try/except block to the function, returning the error if it occurs.
# allows passing an error object consisting of a code and message to the caller. 

def add_error(message, code):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                raise APIConnectorError(message, code, e)
        return wrapper
    return decorator