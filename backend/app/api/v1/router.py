"""
API v1 Router

Main router that includes all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, projects, materials, participants, tests, student, analytics

api_router = APIRouter()

# Include all routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

api_router.include_router(
    projects.router,
    prefix="/projects",
    tags=["Projects"],
)

api_router.include_router(
    materials.router,
    prefix="/materials",
    tags=["Materials"],
)

api_router.include_router(
    participants.router,
    prefix="/participants",
    tags=["Participants"],
)

api_router.include_router(
    tests.router,
    prefix="/tests",
    tags=["Tests"],
)

api_router.include_router(
    student.router,
    prefix="/student",
    tags=["Student"],
)

api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"],
)
