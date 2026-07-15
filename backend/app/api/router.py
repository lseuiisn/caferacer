from fastapi import APIRouter

from app.api.routers import (
    admin,
    admin_courses,
    admin_moderation,
    auth,
    cafes,
    community,
    courses,
    crews,
    daily_courses,
    drive_records,
    lightning_courses,
    places,
    profile,
    rankings,
    recommendations,
    uploads,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(cafes.router)
api_router.include_router(cafes.me_router)
api_router.include_router(courses.router)
api_router.include_router(recommendations.router)
api_router.include_router(drive_records.router)
api_router.include_router(drive_records.me_router)
api_router.include_router(lightning_courses.router)
api_router.include_router(places.router)
api_router.include_router(daily_courses.router)
api_router.include_router(rankings.router)
api_router.include_router(profile.router)
api_router.include_router(community.router)
api_router.include_router(crews.router)
api_router.include_router(uploads.router)
api_router.include_router(admin.router)
api_router.include_router(admin_courses.router)
api_router.include_router(admin_moderation.router)
api_router.include_router(daily_courses.admin_router)
