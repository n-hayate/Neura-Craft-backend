import logging
import os
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File as FastAPIFile,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from app.api.deps import get_current_user, get_db_session
from app.db.models.user import User
from app.schemas.file import (
    FileCreate,
    FileMetadataUpdate,
    FileRead,
    FileSearchResponse,
    FileWithLink,
)
from app.schemas.reference import ReferenceCreate, ReferenceRead
from app.schemas.dashboard import DashboardResponse
from app.services.blob_service import BlobService
from app.services.file_service import FileService
from app.services.reference_service import ReferenceService
from app.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["Files"])


def _extract_metadata_from_filename(filename: str) -> dict[str, str | None]:
    stem, _ = os.path.splitext(filename)
    parts = stem.split("_")
    
    fields = ["application", "issue", "ingredient", "customer", "trial_id", "author"]
    values = {field: None for field in fields}
    
    # 先頭から順にマッピングする
    for i, part in enumerate(parts):
        if i >= len(fields):
            break
        cleaned = part.strip()
        values[fields[i]] = cleaned if cleaned else None
            
    return values


def _to_file_with_link(file_obj, blob_service: BlobService | None = None) -> FileWithLink:
    is_dict = isinstance(file_obj, dict)
    file_id = file_obj.get("id") if is_dict else file_obj.id
    blob_path = file_obj.get("blob_path") if is_dict else file_obj.blob_path

    download_link = None
    if blob_service and blob_path:
        try:
            download_link = blob_service.generate_sas_url(blob_path)
        except Exception as exc:
            logger.warning("Failed to generate download link for %s: %s", file_id, exc)

    return FileWithLink(
        id=file_id,
        file_name=file_obj.get("file_name") if is_dict else file_obj.original_name,
        application=file_obj.get("application") if is_dict else file_obj.application,
        issue=file_obj.get("issue") if is_dict else file_obj.issue,
        ingredient=file_obj.get("ingredient") if is_dict else file_obj.ingredient,
        customer=file_obj.get("customer") if is_dict else file_obj.customer,
        trial_id=file_obj.get("trial_id") if is_dict else file_obj.trial_id,
        author=file_obj.get("author") if is_dict else file_obj.author,
        status=file_obj.get("status") if is_dict else file_obj.status,
        updated_at=file_obj.get("updated_at") if is_dict else getattr(file_obj, "updated_at", None),
        download_link=download_link,
    )


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """ダッシュボード用データ取得"""
    service = DashboardService(db)
    return service.get_dashboard_data()


@router.get("/", response_model=list[FileRead])
def list_files(
    mine_only: bool = Query(False, description="自分のファイルのみ表示する場合はtrue"),
    limit: int = 50,
    offset: int = 0,
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    service = FileService(db)
    owner_id = current_user.id if mine_only else None
    return service.list_by_owner(owner_id=owner_id, limit=limit, offset=offset)


@router.get("/search", response_model=FileSearchResponse)
def search_files(
    q: str | None = Query(None, description="ファイル名での部分一致検索"),
    mine_only: bool = Query(False, description="自分のファイルのみ検索する場合はtrue"),
    application: str | None = Query(None),
    issue: str | None = Query(None),
    ingredient: str | None = Query(None),
    customer: str | None = Query(None),
    trial_id: str | None = Query(None),
    author: str | None = Query(None),
    status_filter: str | None = Query(None),
    sort_by: str = Query("updated_at_desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """ファイル検索 API（Step4でAzure Searchに置き換え予定）"""
    service = FileService(db)
    owner_id = current_user.id if mine_only else None

    total_count, files = service.search(
        owner_id=owner_id,
        q=q,
        application=application,
        issue=issue,
        ingredient=ingredient,
        customer=customer,
        trial_id=trial_id,
        author=author,
        status=status_filter,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )

    blob_service = BlobService()
    results = [_to_file_with_link(f, blob_service) for f in files]
    return FileSearchResponse(total_count=total_count, files=results)


@router.post("/{file_id}/download", response_model=dict)
def download_file(
    file_id: str,
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    ファイルのダウンロードリンクを取得し、ダウンロード履歴を記録する。
    """
    file_service = FileService(db)
    # ファイル存在確認
    file_obj = file_service.get(file_id)

    # 履歴記録
    file_service.record_download(file_id, current_user.id)

    # SAS URL生成
    blob_service = BlobService()
    try:
        sas_url = blob_service.generate_sas_url(file_obj.blob_path, expiry_minutes=60)
    except Exception as e:
        logger.error("Failed to generate SAS URL for %s: %s", file_id, e)
        raise HTTPException(status_code=500, detail="Could not generate download URL")

    return {"download_url": sas_url}


@router.get("/{file_id}", response_model=FileWithLink)
def get_file_metadata(
    file_id: str,
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """単一ファイルのメタデータ取得"""
    service = FileService(db)
    file_obj = service.get(file_id)

    # 所有者以外には非公開（将来的にロール/権限で拡張可能）
    if file_obj.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    blob_service = BlobService()
    return _to_file_with_link(file_obj, blob_service)


@router.get("/{file_id}/preview-url", response_model=dict)
def get_preview_url(
    file_id: str,
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    ファイルのプレビュー用URL (SAS付き) を取得する。
    Officeファイルの場合は、Office Online Viewerの埋め込みURLを返す。
    PDFの場合は、SAS付きの直接リンクを返す。
    """
    file_service = FileService(db)
    file_obj = file_service.get(file_id)

    filename = file_obj.original_name
    _, ext = os.path.splitext(filename)
    ext = ext.lower() if ext else ""

    blob_service = BlobService()
    try:
        sas_url = blob_service.generate_sas_url(file_obj.blob_path, expiry_minutes=60)
    except Exception as e:
        logger.error("Failed to generate SAS URL for %s: %s", file_id, e)
        raise HTTPException(status_code=500, detail="Could not generate preview URL")

    if sas_url.startswith("file://"):
        return {"preview_url": sas_url, "type": "local"}

    from urllib.parse import quote

    encoded_sas_url = quote(sas_url, safe="")

    if ext in [".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"]:
        preview_url = f"https://view.officeapps.live.com/op/embed.aspx?src={encoded_sas_url}"
        return {"preview_url": preview_url, "type": "office"}
    if ext == ".pdf":
        return {"preview_url": sas_url, "type": "pdf"}
    return {"preview_url": sas_url, "type": "other"}


@router.post("/{file_id}/reference", response_model=ReferenceRead)
def create_reference(
    file_id: str,
    payload: ReferenceCreate,
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """ファイル参照（Reference）作成"""
    file_service = FileService(db)
    # ファイル存在確認
    file_service.get(file_id)
    
    service = ReferenceService(db)
    return service.create(file_id, current_user.id, payload)


@router.post("/", response_model=FileRead, status_code=201)
async def upload_file(
    uploaded_file: UploadFile = FastAPIFile(...),
    file_status: str = Form("active"),
    application: str | None = Form(None),
    issue: str | None = Form(None),
    ingredient: str | None = Form(None),
    customer: str | None = Form(None),
    trial_id: str | None = Form(None),
    author: str | None = Form(None),
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    if not uploaded_file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    data = await uploaded_file.read()
    logger.info("Uploading file: %s (%d bytes)", uploaded_file.filename, len(data))

    file_id = str(uuid4())
    original_name = uploaded_file.filename
    _, ext = os.path.splitext(original_name)
    extension = ext.lstrip(".")
    blob_name = f"{file_id}.{extension}" if extension else file_id

    metadata = {
        "original_name": original_name,
        "status": file_status,
        "file_id": file_id,
        "application": application,
        "issue": issue,
        "ingredient": ingredient,
        "customer": customer,
        "trial_id": trial_id,
        "author": author,
    }
    
    if current_user and getattr(current_user, "id", None):
        metadata["owner_id"] = str(current_user.id)

    async with BlobService() as blob_service:
        try:
            blob_path, _ = await blob_service.upload_blob(
                blob_name,
                data,
                content_type=uploaded_file.content_type,
                metadata=metadata,
            )
        except Exception as exc:
            logger.exception("Failed to upload blob")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Blob upload failed: {exc}",
            ) from exc

        file_service = FileService(db)
        payload = FileCreate(
            id=file_id,
            blob_path=blob_path,
            original_name=original_name,
            application=application,
            issue=issue,
            ingredient=ingredient,
            customer=customer,
            trial_id=trial_id,
            author=author,
            status=file_status,
            owner_id=current_user.id,
        )

        try:
            record = file_service.create(payload)
        except Exception as exc:
            await blob_service.delete_blob(blob_path)
            logger.exception("Failed to create DB record, blob deleted")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to persist file metadata.",
            ) from exc

    return record


@router.put("/{file_id}")
def update_file_metadata(
    file_id: str,
    payload: FileMetadataUpdate,
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """ファイルメタデータ更新（暫定的に所有者のみ許可。将来ロールで管理者限定に変更可能）"""
    service = FileService(db)
    file_obj = service.get(file_id)

    if file_obj.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    updated = service.update_metadata(file_id, payload)
    return {"message": "File metadata updated successfully", "file_id": str(updated.id)}


@router.delete("/{file_id}", status_code=204)
async def delete_file(
    file_id: str,
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    file_service = FileService(db)
    file_obj = file_service.get(file_id)
    if file_obj.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    async with BlobService() as blob_service:
        await blob_service.delete_blob(file_obj.blob_path)
    file_service.delete(file_id)
