from supabase import create_client, Client,SupabaseException
from config import Settings, get_settings
import logging

logger = logging.getLogger(__name__)

class SupabaseClient:
    def __init__(self, config: Settings | None = None):
        logger.info("Initializing Supabase client...")
        config = config or get_settings()
        self.supabase_url = config.supabase_url
        self.supabase_publishable_key = config.supabase_publishable_key
        self.supabase_service_role_key = config.supabase_service_role_key

    def connect_to_supabase(self) -> Client:
        """Establish a connection to the Supabase client."""
        try:
            logger.info("Connecting to Supabase...")
            return create_client(self.supabase_url, self.supabase_service_role_key)
        except SupabaseException as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise RuntimeError(f"Failed to initialize Supabase client: {e}") from e

