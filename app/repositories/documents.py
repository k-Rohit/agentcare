from postgrest.exceptions import APIError
from storage3.exceptions import StorageApiError

from config import get_settings
from app.services.supabase.factory import get_supabase_client


def _bucket() -> str:
    return get_settings().documents_bucket


def insert_patient_document(patient_id: str, document_type: str, file_path: str, document_date: str) -> dict:
    try:
        response = (
            get_supabase_client()
            .table("patient_documents")
            .insert({
                "patient_id": patient_id,
                "document_type": document_type,
                "file_path": file_path,
                "document_date": document_date,
            })
            .execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to store document for patient {patient_id}: {e}") from e
    return response.data[0]


def list_patient_documents(patient_id: str) -> list[dict]:
    try:
        response = (
            get_supabase_client()
            .table("patient_documents")
            .select("*")
            .eq("patient_id", patient_id)
            .execute()
        )
    except APIError as e:
        raise RuntimeError(f"Failed to fetch documents for patient {patient_id}: {e}") from e
    return response.data or []


def upload_patient_document(patient_id: str, filename: str, file_content: bytes) -> str:
    path = f"{patient_id}/{filename}"
    try:
        get_supabase_client().storage.from_(_bucket()).upload(path, file_content)
    except StorageApiError as e:
        raise RuntimeError(f"Failed to upload document for patient {patient_id}: {e}") from e
    return path


def create_document_signed_url(file_path: str, expires_in: int) -> str:
    try:
        response = get_supabase_client().storage.from_(_bucket()).create_signed_url(file_path, expires_in)
    except StorageApiError as e:
        raise RuntimeError(f"Failed to generate signed URL for {file_path}: {e}") from e
    return response["signedURL"]

