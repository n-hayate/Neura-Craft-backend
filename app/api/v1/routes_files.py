import logging
import os

from fastapi import APIRouter, Depends, File as FastAPIFile, Form, HTTPException, Query, UploadFile, status

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
    final_product: str | None = Query(None),
    issue: str | None = Query(None),
    ingredient: str | None = Query(None),
    customer: str | None = Query(None),
    trial_id: str | None = Query(None),
    author: str | None = Query(None),
    sort_by: str = Query("updated_at_desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """ファイル検索 API"""
    service = FileService(db)
    owner_id = current_user.id if mine_only else None
    
    total_count, files = service.search(
        owner_id=owner_id,
        q=q,
        final_product=final_product,
        issue=issue,
        ingredient=ingredient,
        customer=customer,
        trial_id=trial_id,
        author=author,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )

    results: list[FileWithLink] = []
    for f in files:
        download_link = f.azure_blob_url  # 現状は保存済みURLをそのまま返す（本番ではSAS発行に差し替え可能）
        results.append(
            FileWithLink(
                id=f.id,
                file_name=f.original_filename,
                final_product=f.final_product,
                issue=f.issue,
                ingredient=f.ingredient,
                customer=f.customer,
                trial_id=f.trial_id,
                author=f.author,
                status=f.status,
                updated_at=getattr(f, "updated_at", None),
                download_link=download_link,
            )
        )

    return FileSearchResponse(total_count=total_count, files=results)


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

    download_link = file_obj.azure_blob_url
    return FileWithLink(
        id=file_obj.id,
        file_name=file_obj.original_filename,
        final_product=file_obj.final_product,
        issue=file_obj.issue,
        ingredient=file_obj.ingredient,
        customer=file_obj.customer,
        trial_id=file_obj.trial_id,
        author=file_obj.author,
        status=file_obj.status,
        updated_at=getattr(file_obj, "updated_at", None),
        download_link=download_link,
    )


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
    
    if file_obj.is_preview_hidden:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Preview is disabled for this file")

    # 拡張子チェック
    filename = file_obj.original_filename
    _, ext = os.path.splitext(filename)
    ext = ext.lower() if ext else ""
    
    # Blob ServiceでSAS URL生成
    blob_service = BlobService()
    try:
        sas_url = blob_service.generate_sas_url(file_obj.blob_name, expiry_minutes=60)
    except Exception as e:
        logger.error(f"Failed to generate SAS URL for file {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not generate preview URL")
        
    # ローカル環境(file://)の場合はOffice Online Viewerは使えないため、そのまま返す
    if sas_url.startswith("file://"):
        return {"preview_url": sas_url, "type": "local"}
    
    # URLエンコード (Office Online Viewerに渡すため)
    from urllib.parse import quote
    encoded_sas_url = quote(sas_url, safe="")
    
    if ext in [".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"]:
        # Office Online Viewer
        # srcパラメータにエンコードされたURLを渡す
        preview_url = f"https://view.officeapps.live.com/op/embed.aspx?src={encoded_sas_url}"
        return {"preview_url": preview_url, "type": "office"}
    elif ext == ".pdf":
        # PDFはブラウザで直接開けるのでSAS URLそのまま
        return {"preview_url": sas_url, "type": "pdf"}
    else:
        # その他のファイルはプレビュー非対応（またはダウンロードさせる）
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
    final_product: str = Form(...),
    issue: str = Form(...),
    ingredient: str = Form(...),
    customer: str = Form(...),
    trial_id: str = Form(...),
    author: str | None = Form(None),
    file_extension: str | None = Form(None),
    file_status: str = Form("active"),
    is_preview_hidden: bool = Form(False),
    db=Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    try:
        data = await uploaded_file.read()
        logger.info(f"Uploading file: {uploaded_file.filename}, size: {len(data)} bytes")

        # ファイル拡張子が指定されていない場合は、元のファイル名から抽出
        if not file_extension:
            _, ext = os.path.splitext(uploaded_file.filename)
            file_extension = ext.lstrip(".") if ext else ""

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
            final_product=final_product,
            issue=issue,
            ingredient=ingredient,
            customer=customer,
            trial_id=trial_id,
            author=author,
            file_extension=file_extension,
            status=file_status,
            is_preview_hidden=is_preview_hidden,
        )
        return file_service.create(payload, blob_name=blob_name, blob_url=blob_url)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error during file upload")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}",
        )


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
