from fastapi import APIRouter

from app.api.v1.endpoints import body_metrics, breaks, export, habits, stats, workouts

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(habits.router)
api_router.include_router(workouts.router)
api_router.include_router(body_metrics.router)
api_router.include_router(breaks.router)
api_router.include_router(stats.router)
api_router.include_router(export.router)
