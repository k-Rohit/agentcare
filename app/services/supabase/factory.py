from functools import lru_cache
from supabase import Client
from app.services.supabase.client import SupabaseClient

@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    client = SupabaseClient().connect_to_supabase()
    return client
