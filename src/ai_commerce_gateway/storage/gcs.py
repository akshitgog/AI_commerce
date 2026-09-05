"""Google Cloud Storage StorageService implementation."""

import json

from google.api_core.exceptions import GoogleAPIError
from google.cloud import storage

from ai_commerce_gateway.contracts.models import StoredImage
from ai_commerce_gateway.contracts.services import StorageService
from ai_commerce_gateway.core.ids import new_id


class GCSStorageService(StorageService):
    """Storage adapter persisting image bytes to Google Cloud Storage."""

    def __init__(self, bucket: str, credentials_json: str | None = None) -> None:
        if credentials_json:
            credentials = json.loads(credentials_json)
            self.client = storage.Client.from_service_account_info(credentials)
        else:
            # Use default credentials (from GOOGLE_APPLICATION_CREDENTIALS env var)
            self.client = storage.Client()

        self.bucket_name = bucket
        self.bucket = self.client.bucket(bucket)

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

        try:
            blob = self.bucket.blob(storage_path)
            blob.upload_from_string(content, content_type=content_type)
        except GoogleAPIError as e:
            raise RuntimeError(f"Failed to upload to GCS: {e}") from e

        public_url = self.get_public_url(storage_path=storage_path)
        return StoredImage(storage_path=storage_path, public_url=public_url)

    def delete_product_image(self, *, storage_path: str) -> None:
        try:
            blob = self.bucket.blob(storage_path)
            blob.delete()
        except GoogleAPIError as e:
            raise RuntimeError(f"Failed to delete from GCS: {e}") from e

    def get_public_url(self, *, storage_path: str) -> str:
        return f"https://storage.googleapis.com/{self.bucket_name}/{storage_path}"
