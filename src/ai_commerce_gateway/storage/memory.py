"""In-memory StorageService implementation for tests and local development."""

from ai_commerce_gateway.contracts.models import StoredImage
from ai_commerce_gateway.contracts.services import StorageService
from ai_commerce_gateway.core.ids import new_id


class InMemoryStorageService(StorageService):
    """Storage adapter holding image bytes in an in-memory dictionary."""

    def __init__(self, base_url: str = "https://storage.local") -> None:
        self._base_url = base_url.rstrip("/")
        self._files: dict[str, bytes] = {}
        self._content_types: dict[str, str] = {}

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
        storage_path = f"merchants/{merchant_id}/products/{product_id}/{image_id}_{clean_filename}"
        self._files[storage_path] = content
        self._content_types[storage_path] = content_type
        public_url = self.get_public_url(storage_path=storage_path)
        return StoredImage(storage_path=storage_path, public_url=public_url)

    def delete_product_image(self, *, storage_path: str) -> None:
        self._files.pop(storage_path, None)
        self._content_types.pop(storage_path, None)

    def get_public_url(self, *, storage_path: str) -> str:
        return f"{self._base_url}/{storage_path}"

    def exists(self, storage_path: str) -> bool:
        return storage_path in self._files

    def get_content(self, storage_path: str) -> bytes | None:
        return self._files.get(storage_path)
