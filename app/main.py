from fastapi import FastAPI
from app.api.routes.staff import router as staff_router

app = FastAPI()

app.include_router(staff_router, prefix="/staff", tags=["staff"])
