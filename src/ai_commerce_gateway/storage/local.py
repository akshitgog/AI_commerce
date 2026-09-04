"""Filesystem-backed StorageService implementation."""

from pathlib import Path

from ai_commerce_gateway.contracts.models import StoredImage
from ai_commerce_gateway.contracts.services import StorageService
from ai_commerce_gateway.core.ids import new_id


class LocalStorageService(StorageService):
    """Storage adapter persisting image bytes to a local filesystem directory."""

    def __init__(self, base_directory: Path | str, base_url: str = "/media") -> None:
        self._base_dir = Path(base_directory).resolve()
        self._base_url = base_url.rstrip("/")
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def upload_product_image(
        self,
        *,
        merchant_id: str,
        product_id: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> StoredImage:
        image_id = new_id("pimg")
        clean_filename = filename.replace("/", "_").replace("\\", "_")
        rel_path = f"merchants/{merchant_id}/products/{product_id}/{image_id}_{clean_filename}"
        full_path = self._base_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)

        storage_path = rel_path.replace("\\", "/")
        public_url = self.get_public_url(storage_path=storage_path)
        return StoredImage(storage_path=storage_path, public_url=public_url)

    def delete_product_image(self, *, storage_path: str) -> None:
        full_path = self._base_dir / storage_path
        if full_path.is_file():
            full_path.unlink()

    def get_public_url(self, *, storage_path: str) -> str:
        clean_path = storage_path.lstrip("/")
        return f"{self._base_url}/{clean_path}"

    def exists(self, storage_path: str) -> bool:
        full_path = self._base_dir / storage_path
        return full_path.is_file()
