from postgrest.exceptions import APIError
from storage3.exceptions import StorageApiError
from app.services.supabase.factory import get_supabase_client
import logging

logger = logging.getLogger(__name__)

DOCUMENTS_BUCKET = "patient-documents"

def store_document(patient_id: str, document_type: str, file_path: str, document_date: str) -> dict:
    """Save metadata for a document already uploaded for a patient.

    Use this after a document has been classified (document_type decided by
    the agent, not this function) and its file already stored somewhere —
    this only persists the metadata pointing at it, it doesn't handle the
    actual file upload. Does not check for duplicates; the same document
    could currently be stored more than once.

    Args:
        patient_id: The patient's id (patient_profiles.id, not user_id).
        document_type: One of "lab_report", "ecg", "imaging", "prescription",
            "discharge_summary", "referral", "other".
        file_path: Where the actual file content is stored (e.g. a storage
            bucket path), not the file content itself.
        document_date: The date the document is from (not when it was
            uploaded), as an ISO date string.

    Returns:
        The newly created patient_documents row as a dict.

    Raises:
        RuntimeError: If the insert fails, e.g. document_type isn't one of
            the allowed values.
    """
    client = get_supabase_client()
    try:
        response = client.table("patient_documents").insert({
            "patient_id": patient_id,
            "document_type": document_type,
            "file_path": file_path,
            "document_date": document_date
        }).execute()
    except APIError as e:
        logger.error(f"Failed to store document for patient {patient_id}: {e}")
        raise
    return response.data[0]

def get_documents(patient_id: str) -> list[dict]:
    """List every document on file for a patient.

    Use this to show a patient their uploaded documents, or to check what's
    already on file before deciding whether more are needed.

    Args:
        patient_id: The patient's id (patient_profiles.id, not user_id).

    Returns:
        A list of patient_documents rows. Empty list if the patient has no
        documents on file.
    """
    client = get_supabase_client()
    try:
        response = client.table("patient_documents").select("*") \
                   .eq("patient_id",patient_id) \
                   .execute()
    except APIError as e:
        logger.error(f"Failed the fetch the document for patient {patient_id}: {e}")
        raise
    return response.data if response.data else []


def upload_document(patient_id: str, filename: str, file_content: bytes) -> str:
    """Upload a document's raw file content to private storage.

    Use this before store_document — this handles the actual file bytes;
    store_document only saves the resulting path as metadata afterward. The
    bucket is private, so nothing uploaded here is reachable by a direct
    public URL — only via get_document_url's temporary signed links.

    Args:
        patient_id: The patient's id, used to namespace the file's path so
            different patients' files can't collide.
        filename: The original filename, e.g. "ecg_scan.pdf".
        file_content: The raw file bytes to upload.

    Returns:
        The storage path the file was saved under — pass this straight into
        store_document as its file_path argument.

    Raises:
        RuntimeError: If the upload fails.
    """
    client = get_supabase_client()
    path = f"{patient_id}/{filename}"
    try:
        client.storage.from_(DOCUMENTS_BUCKET).upload(path, file_content)
    except StorageApiError as e:
        raise RuntimeError(f"Failed to upload document for patient {patient_id}: {e}") from e
    return path


def get_document_url(file_path: str, expires_in: int = 3600) -> str:
    """Get a temporary, expiring URL to view or download a stored document.

    Use this whenever a document actually needs to be shown to someone
    (patient or doctor) — never treat file_path itself as a link, since the
    bucket is private and file_path alone grants no access.

    Args:
        file_path: The storage path (patient_documents.file_path) to link to.
        expires_in: How many seconds the URL stays valid for. Defaults to
            one hour.

    Returns:
        A signed URL string that grants temporary access to the file.

    Raises:
        RuntimeError: If generating the signed URL fails, e.g. no file
            exists at that path.
    """
    client = get_supabase_client()
    try:
        response = client.storage.from_(DOCUMENTS_BUCKET).create_signed_url(file_path, expires_in)
    except StorageApiError as e:
        raise RuntimeError(f"Failed to generate signed URL for {file_path}: {e}") from e
    return response["signedURL"]
