"""Safe path resolution for document downloads."""

from pathlib import Path

from fastapi import HTTPException

from app.config import DATA_DIR, DOCUMENTS_DIR


def resolve_document_path(rel_path: str) -> Path:
    if not rel_path or ".." in rel_path:
        raise HTTPException(status_code=403, detail="Forbidden")

    full_path = (DATA_DIR / rel_path).resolve()
    allowed_root = DOCUMENTS_DIR.resolve()

    if not str(full_path).startswith(str(allowed_root)):
        raise HTTPException(status_code=403, detail="Forbidden")

    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="Not found")

    return full_path
