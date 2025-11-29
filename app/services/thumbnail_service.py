import os
import shutil
import logging
import tempfile
from pathlib import Path
from app.services.blob_service import BlobService
from app.core.config import get_settings

# Pillowがインストールされていれば使う、なければ簡易的なバイト列を返す
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

logger = logging.getLogger(__name__)
settings = get_settings()

class ThumbnailService:
    def __init__(self):
        self.thumb_blob_service = BlobService(container_name=settings.azure_blob_thumbnails_container)
        self.files_blob_service = BlobService(container_name=settings.azure_blob_files_container)

    def get_thumbnail_url(self, file_id: str) -> str | None:
        """サムネイルのURLを返す"""
        blob_name = f"{file_id}.png"
        if self.thumb_blob_service.blob_exists(blob_name):
             if self.thumb_blob_service.use_local_storage:
                 return f"file://{(self.thumb_blob_service.storage_path / blob_name).absolute()}"
             else:
                 return self.thumb_blob_service.client.get_blob_client(self.thumb_blob_service.container_name, blob_name).url
        return None

    def get_or_generate_thumbnail(self, file_id: str, source_blob_name: str, file_ext: str) -> bytes:
        """
        サムネイルを取得、なければダミー画像を生成して返す。
        （LibreOffice/pdftoppm依存を排除したバージョン）
        """
        thumb_blob_name = f"{file_id}.png"

        # 1. 既存チェック
        if self.thumb_blob_service.blob_exists(thumb_blob_name):
            logger.info(f"Thumbnail exists for {file_id}, downloading...")
            return self.thumb_blob_service.download_blob(thumb_blob_name)

        # 2. ダミー生成処理
        logger.info(f"Generating dummy thumbnail for {file_id} (ext: {file_ext})")
        
        try:
            # 一時出力先
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_dest:
                tmp_dest_path = Path(tmp_dest.name)

            # ダミー画像を生成
            self._create_dummy_image(tmp_dest_path, file_ext)
            
            # 生成されたPNGを読み込む
            thumb_data = tmp_dest_path.read_bytes()
            
            # Blobへ直接アップロード (UUID付与回避)
            self._upload_thumbnail_direct(thumb_blob_name, thumb_data)

            return thumb_data

        finally:
            if 'tmp_dest_path' in locals() and tmp_dest_path.exists():
                tmp_dest_path.unlink()

    def _create_dummy_image(self, dest_path: Path, file_ext: str):
        """Pillowを使ってダミー画像を生成する"""
        if not HAS_PILLOW:
            # Pillowがない場合は適当な1x1ピクセルのPNGバイナリを書き込むなどの対応も可能だが
            # ここではエラーログを出して空ファイルを作成（またはエラー）
            logger.warning("Pillow not installed. Creating empty file.")
            dest_path.write_bytes(b"") 
            return

        # 画像サイズと色
        width, height = 300, 400
        color = (240, 240, 240) # 薄いグレー
        
        # 拡張子ごとの色分け（おまけ）
        ext = file_ext.lower()
        if "pdf" in ext:
            header_color = (200, 50, 50) # 赤
        elif "xls" in ext:
            header_color = (50, 150, 50) # 緑
        elif "doc" in ext:
            header_color = (50, 50, 200) # 青
        elif "ppt" in ext:
            header_color = (200, 100, 50) # オレンジ
        else:
            header_color = (100, 100, 100)

        img = Image.new('RGB', (width, height), color)
        draw = ImageDraw.Draw(img)

        # 枠線
        draw.rectangle([(0, 0), (width-1, height-1)], outline=header_color, width=5)
        
        # ヘッダー帯
        draw.rectangle([(0, 0), (width, 50)], fill=header_color)
        
        # テキスト描画（フォントがない環境も考慮してデフォルトフォント）
        try:
            # Windowsの標準的なフォントパスなどを探してもよいが、load_defaultを使う
            # Pillow 10以降は size指定可能だが、古いとできない場合も
            # font = ImageFont.load_default(size=20) 
            font = ImageFont.load_default()
        except Exception:
            font = None

        text = f"{file_ext}\nPreview"
        
        # 中央寄せっぽい位置に描画（簡易）
        draw.text((width//2, height//2), text, fill=(0, 0, 0), anchor="mm", font=font)
        
        img.save(dest_path, "PNG")

    def _upload_thumbnail_direct(self, blob_name: str, data: bytes):
        """BlobServiceのUUID付与を回避して直接指定名でアップロード"""
        if self.thumb_blob_service.use_local_storage:
             (self.thumb_blob_service.storage_path / blob_name).write_bytes(data)
        else:
             blob_client = self.thumb_blob_service.client.get_blob_client(
                 self.thumb_blob_service.container_name, blob_name
             )
             from azure.storage.blob import ContentSettings
             blob_client.upload_blob(
                 data, 
                 overwrite=True, 
                 content_settings=ContentSettings(content_type="image/png")
             )
