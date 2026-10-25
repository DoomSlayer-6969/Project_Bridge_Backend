from fastapi import APIRouter

from app.api.v1 import auth, conversations, users
from app.api.v1.endpoints import health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(conversations.router)
