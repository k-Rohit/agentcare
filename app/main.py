from fastapi import FastAPI
from app.api.routes.staff import router as staff_router
from app.api.routes.health import router as health_router

app = FastAPI()

app.include_router(staff_router, prefix="/staff", tags=["staff"])
app.include_router(health_router, tags=["health"])
