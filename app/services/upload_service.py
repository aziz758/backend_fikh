from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from fastapi.responses import FileResponse


MAX_IMAGE_UPLOAD_BYTES = 5 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
PUBLIC_UPLOADS_DIR = "uploads"
PUBLIC_TECHNICIAN_PROFILE_UPLOAD_DIR = "uploads/technician_profiles"
LEGACY_TECHNICIAN_DOCUMENTS_DIR = "uploads/documents"
PRIVATE_TECHNICIAN_DOCUMENTS_DIR = "private_uploads/technician_documents"
ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg": "jpg",
    ".jpeg": "jpg",
    ".png": "png",
    ".webp": "webp",
}


@dataclass(frozen=True)
class SavedUpload:
    filename: str
    path: str
    url: str | None = None


def _resolve_image_extension(upload_file) -> str:
    content_type = (getattr(upload_file, "content_type", None) or "").lower()
    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type. Allowed types: JPEG, PNG, WebP.",
        )

    original_name = getattr(upload_file, "filename", None) or ""
    original_suffix = Path(original_name).suffix.lower()
    if original_suffix and original_suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image extension. Allowed extensions: jpg, jpeg, png, webp.",
        )

    resolved_extension = ALLOWED_IMAGE_CONTENT_TYPES[content_type]
    if original_suffix and ALLOWED_IMAGE_EXTENSIONS[original_suffix] != resolved_extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image extension does not match content type.",
        )

    return resolved_extension


def save_validated_image_upload(
    upload_file,
    upload_dir: str,
    *,
    public_prefix: str | None = None,
) -> SavedUpload:
    if not upload_file or not hasattr(upload_file, "file"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image upload")

    extension = _resolve_image_extension(upload_file)
    filename = f"{uuid4()}.{extension}"
    target_dir = Path(upload_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filename

    total_size = 0
    try:
        upload_file.file.seek(0)
        with target_path.open("wb") as output:
            while True:
                chunk = upload_file.file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_IMAGE_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Image is too large. Maximum size is 5 MB.",
                    )
                output.write(chunk)
    except HTTPException:
        if target_path.exists():
            target_path.unlink()
        raise

    if total_size == 0:
        if target_path.exists():
            target_path.unlink()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image file is empty")

    normalized_path = target_path.as_posix()
    url = f"{public_prefix.rstrip('/')}/{filename}" if public_prefix else None
    return SavedUpload(filename=filename, path=normalized_path, url=url)


def public_upload_url(stored_value: str | None) -> str | None:
    if not stored_value:
        return None
    normalized = stored_value.replace("\\", "/")
    if normalized.startswith("/"):
        return normalized
    if normalized.startswith(f"{PUBLIC_UPLOADS_DIR}/"):
        return f"/{normalized}"
    return normalized


def protected_upload_file_response(
    stored_path: str | None,
    *,
    allowed_dirs: list[str],
) -> FileResponse:
    if not stored_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    requested_path = Path(stored_path).resolve()
    allowed_roots = [Path(directory).resolve() for directory in allowed_dirs]
    if not any(requested_path == root or requested_path.is_relative_to(root) for root in allowed_roots):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if not requested_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return FileResponse(path=str(requested_path), filename=requested_path.name)
