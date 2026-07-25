from fastapi import FastAPI
import uvicorn
from app.api.routes.staff import router as staff_router
from app.api.routes.health import router as health_router
from app.api.routes.requests import router as chat_router
from app.api.routes.patient import router as patient_router

app = FastAPI()

app.include_router(staff_router, prefix="/agentcare/api/v1", tags=["staff"])
app.include_router(health_router, prefix="/agentcare/api/v1", tags=["health"])
app.include_router(chat_router, prefix="/agentcare/api/v1", tags=["chat"])
app.include_router(patient_router, prefix="/agentcare/api/v1", tags=["patient"])

if __name__ == "__main__":
    uvicorn.run(app=app)
