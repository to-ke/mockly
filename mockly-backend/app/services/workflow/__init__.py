"""
Workflow service package; exposes the FastAPI router for inclusion in app.main.
"""

from .router import router

__all__ = ["router"]
