from functools import lru_cache
from supabase import Client
from app.services.supabase.client import SupabaseClient

@lru_cache
def get_supabase_client() -> Client:
    client = SupabaseClient().connect_to_supabase()
    return client


if __name__ == "__main__":
    print(get_supabase_client().table("profiles").select("*").execute())
