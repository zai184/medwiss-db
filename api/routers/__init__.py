"""API routers package."""

from api.routers.classifications import router as classifications_router
from api.routers.entries import router as entries_router
from api.routers.search import router as search_router

__all__ = ["classifications_router", "entries_router", "search_router"]
