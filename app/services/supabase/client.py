import os
import sys
from supabase import create_client, Client
sys.path.append("")
from config import get_settings

supabase: Client = create_client(
    url=get_settings().supabase_url,
    key=get_settings().supabase_publishable_key,
)

print(supabase.table("users").select("*").execute())
