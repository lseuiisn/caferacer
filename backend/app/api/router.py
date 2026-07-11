from fastapi import APIRouter

from app.api.routers import auth, cafes, courses

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(cafes.router)
api_router.include_router(courses.router)
