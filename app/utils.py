import secrets
import logging

logger = logging.getLogger(__name__)

def create_temporary_password(length: int = 12) -> str:
    """Generate a secure temporary password."""
    logger.info(f"Generating a temporary password of length {length}...")
    temp_password = secrets.token_urlsafe(length)
    return temp_password

