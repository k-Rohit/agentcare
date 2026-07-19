from supabase import create_client, Client
from config import Settings, get_settings

class SupabaseClient:
    def __init__(self, config: Settings | None = None):
        config = config or get_settings()
        self.supabase_url = config.supabase_url
        self.supabase_publishable_key = config.supabase_publishable_key
        self.supabase_service_role_key = config.supabase_service_role_key

    def connect_to_supabase(self) -> Client:
        return create_client(self.supabase_url, self.supabase_service_role_key)

