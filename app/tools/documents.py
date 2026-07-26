from app.services.documents import (
    get_document_url as _get_document_url,
    get_documents as _get_documents,
    store_document as _store_document,
    upload_document as _upload_document,
)


def store_document(patient_id: str, document_type: str, file_path: str, document_date: str) -> dict:
    """Save metadata for a document already uploaded for a patient."""
    return _store_document(patient_id, document_type, file_path, document_date)


def get_documents(patient_id: str) -> list[dict]:
    """List every document on file for a patient."""
    return _get_documents(patient_id)


def upload_document(patient_id: str, filename: str, file_content: bytes) -> str:
    """Upload a document's raw file content to private storage."""
    return _upload_document(patient_id, filename, file_content)


def get_document_url(file_path: str, expires_in: int = 3600) -> str:
    """Get a temporary, expiring URL to view or download a stored document."""
    return _get_document_url(file_path, expires_in)

