from app.repositories import documents as document_repo


def store_document(patient_id: str, document_type: str, file_path: str, document_date: str) -> dict:
    return document_repo.insert_patient_document(patient_id, document_type, file_path, document_date)


def get_documents(patient_id: str) -> list[dict]:
    return document_repo.list_patient_documents(patient_id)


def upload_document(patient_id: str, filename: str, file_content: bytes) -> str:
    return document_repo.upload_patient_document(patient_id, filename, file_content)


def get_document_url(file_path: str, expires_in: int = 3600) -> str:
    return document_repo.create_document_signed_url(file_path, expires_in)

