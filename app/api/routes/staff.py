# This file is used to create the route for the staff and doctors registration and login. It will handle the requests and responses for the staff and doctors registration and login.

from fastapi import APIRouter, HTTPException
from app.schemas.schemas import CreateDoctorRequest
from app.services.supabase.client import SupabaseClient
from app.utils import create_temporary_password

router = APIRouter()

@router.post("/register-doctor")
async def create_doctor(request: CreateDoctorRequest):
    pass

@router.post("/register-staff")
async def create_staff(request: CreateDoctorRequest):
    pass