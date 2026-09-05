"""AWS S3 StorageService implementation."""

import boto3
from botocore.exceptions import ClientError

from ai_commerce_gateway.contracts.models import StoredImage
from ai_commerce_gateway.contracts.services import StorageService
from ai_commerce_gateway.core.ids import new_id


class S3StorageService(StorageService):
    """Storage adapter persisting image bytes to AWS S3."""

    def __init__(self, bucket: str, region: str, access_key: str, secret_key: str) -> None:
        self.bucket = bucket
        self.region = region
        self.s3_client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

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
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=storage_path,
                Body=content,
                ContentType=content_type,
            )
        except ClientError as e:
            raise RuntimeError(f"Failed to upload to S3: {e}") from e

        public_url = self.get_public_url(storage_path=storage_path)
        return StoredImage(storage_path=storage_path, public_url=public_url)

    def delete_product_image(self, *, storage_path: str) -> None:
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=storage_path)
        except ClientError as e:
            raise RuntimeError(f"Failed to delete from S3: {e}") from e

    def get_public_url(self, *, storage_path: str) -> str:
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{storage_path}"
