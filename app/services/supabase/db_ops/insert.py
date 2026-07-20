from app.services.supabase.factory import get_supabase_client

# =================================== Insert Departments ===================================
departments = [
    {"name": "Cardiology", "description": "Heart and cardiovascular care", "active": True},
    {"name": "Orthopedics", "description": "Bones, joints and muscles", "active": True},
    {"name": "Dermatology", "description": "Skin, hair and nail care", "active": True},
    {"name": "General Medicine", "description": "General checkups and common illnesses", "active": True},
    {"name": "Pediatrics", "description": "Child healthcare", "active": True},
    {"name": "Neurology", "description": "Brain, spine and nervous system disorders", "active": True},
    {"name": "Gastroenterology", "description": "Digestive system and gut health", "active": True},
    {"name": "Pulmonology", "description": "Lungs and respiratory conditions", "active": True},
    {"name": "Nephrology", "description": "Kidney health and disorders", "active": True},
    {"name": "Endocrinology", "description": "Hormonal and metabolic conditions, including diabetes and thyroid", "active": True},
    {"name": "ENT", "description": "Ear, nose and throat care", "active": True},
    {"name": "Ophthalmology", "description": "Eye care and vision", "active": True},
    {"name": "Gynecology", "description": "Women's reproductive health", "active": True},
    {"name": "Psychiatry", "description": "Mental health and behavioral care", "active": True},
    {"name": "Oncology", "description": "Cancer diagnosis and treatment coordination", "active": True},
]

client = get_supabase_client()
response = client.table("departments").insert(departments).execute()
print(response.data)

