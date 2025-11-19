import logging

from fastapi import APIRouter, Depends, File as FastAPIFile, HTTPException, UploadFile, status

from app.api.deps import get_current_user, get_db_session
from app.db.models.user import User
from app.schemas.file import FileCreate, FileRead
from app.services.blob_service import BlobService
from app.services.file_service import FileService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("/", response_model=list[FileRead])
def list_files(
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
):
    service = FileService(db)
    return service.list_by_owner(current_user.id, limit=limit, offset=offset)


@router.post("/", response_model=FileRead, status_code=201)
async def upload_file(
    uploaded_file: UploadFile = FastAPIFile(...),
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    try:
        data = await uploaded_file.read()
        logger.info(f"Uploading file: {uploaded_file.filename}, size: {len(data)} bytes")
        
        blob_service = BlobService()
        blob_name, blob_url = blob_service.upload_bytes(
            data,
            uploaded_file.filename,
            uploaded_file.content_type,
        )
        
        file_service = FileService(db)
        payload = FileCreate(
            owner_id=current_user.id,
            original_filename=uploaded_file.filename,
            content_type=uploaded_file.content_type,
            file_size=len(data),
        )
        return file_service.create(payload, blob_name=blob_name, blob_url=blob_url)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error during file upload")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )


@router.delete("/{file_id}", status_code=204)
def delete_file(
    file_id: str,
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    file_service = FileService(db)
    file_obj = file_service.get(file_id)
    if file_obj.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    blob_service = BlobService()
    blob_service.delete_blob(file_obj.blob_name)
    file_service.delete(file_id)

