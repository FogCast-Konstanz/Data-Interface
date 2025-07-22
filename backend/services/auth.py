from flask import request, abort
from config import API_KEY


def require_api_key(func):
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if auth_header != f"Bearer {API_KEY}":
            abort(401, description="Unauthorized: Invalid API key.")
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__  # needed for Flask to recognize route
    return wrapper
