from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from app.api.routes.staff import router as staff_router
from app.api.routes.health import router as health_router
from app.api.routes.requests import router as chat_router
from app.api.routes.patient import router as patient_router

app = FastAPI()

# Allow a separately-served frontend to call the API (safe: we use Bearer tokens,
# not cookies). Harmless when the frontend is served from this same app.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(staff_router, prefix="/agentcare/api/v1", tags=["staff"])
app.include_router(health_router, prefix="/agentcare/api/v1", tags=["health"])
app.include_router(chat_router, prefix="/agentcare/api/v1", tags=["chat"])
app.include_router(patient_router, prefix="/agentcare/api/v1", tags=["patient"])

# Serve the frontend from this same server (same origin as the API → no CORS).
# Mounted last so the API routes above take precedence.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app=app)
