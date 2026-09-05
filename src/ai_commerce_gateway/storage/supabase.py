"""Supabase Storage implementation."""

import httpx

from ai_commerce_gateway.contracts.models import StoredImage
from ai_commerce_gateway.contracts.services import StorageService
from ai_commerce_gateway.core.ids import new_id


class SupabaseStorageService(StorageService):
    """Storage adapter using Supabase Storage API."""

    def __init__(
        self, project_url: str, service_role_key: str, bucket: str = "product-images"
    ) -> None:
        """Initialize Supabase Storage client.

        Args:
            project_url: Supabase project URL (e.g., https://xxx.supabase.co)
            service_role_key: Supabase service role key (for server-side operations)
            bucket: Storage bucket name (default: product-images)
        """
        self.project_url = project_url.rstrip("/")
        self.service_role_key = service_role_key
        self.bucket = bucket
        self.storage_url = f"{self.project_url}/storage/v1"

    def upload_product_image(
        self,
        *,
        merchant_id: str,
        product_id: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> StoredImage:
        """Upload image to Supabase Storage."""
        image_id = new_id("pimg")
        clean_filename = filename.replace("/", "_").replace("\\", "_")
        storage_path = f"merchants/{merchant_id}/products/{product_id}/{image_id}_{clean_filename}"

        # Upload to Supabase Storage
        upload_url = f"{self.storage_url}/object/{self.bucket}/{storage_path}"
        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": content_type,
        }

        response = httpx.post(upload_url, content=content, headers=headers, timeout=30.0)
        response.raise_for_status()

        public_url = self.get_public_url(storage_path=storage_path)
        return StoredImage(storage_path=storage_path, public_url=public_url)

    def delete_product_image(self, *, storage_path: str) -> None:
        """Delete image from Supabase Storage."""
        delete_url = f"{self.storage_url}/object/{self.bucket}/{storage_path}"
        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
        }

        response = httpx.delete(delete_url, headers=headers, timeout=30.0)
        response.raise_for_status()

    def get_public_url(self, *, storage_path: str) -> str:
        """Get public URL for image."""
        return f"{self.project_url}/storage/v1/object/public/{self.bucket}/{storage_path}"
