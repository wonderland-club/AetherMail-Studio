"""WSGI entrypoint for production servers."""

from app import app

application = app

__all__ = ["app", "application"]
