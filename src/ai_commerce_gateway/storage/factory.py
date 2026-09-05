"""Storage service factory."""

from pathlib import Path

from ai_commerce_gateway.contracts.services import StorageService
from ai_commerce_gateway.core.config import Settings
from ai_commerce_gateway.storage.local import LocalStorageService


def create_storage_service(settings: Settings) -> StorageService | None:
    """Create the appropriate storage service based on configuration.

    Args:
        settings: Application settings

    Returns:
        StorageService instance or None if unconfigured

    Raises:
        ValueError: If provider is configured but required settings are missing
    """
    provider = settings.storage_provider

    if provider == "local":
        uploads_dir = Path("uploads")
        return LocalStorageService(uploads_dir, base_url="/media")

    elif provider == "s3":
        # Lazy import to avoid requiring boto3 if not using S3
        from ai_commerce_gateway.storage.s3 import S3StorageService

        if not all(
            [
                settings.storage_bucket,
                settings.aws_region,
                settings.aws_access_key_id,
                settings.aws_secret_access_key,
            ]
        ):
            raise ValueError(
                "S3 storage requires: STORAGE_BUCKET, AWS_REGION, "
                "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
            )

        return S3StorageService(
            bucket=settings.storage_bucket,
            region=settings.aws_region,  # type: ignore
            access_key=settings.aws_access_key_id,  # type: ignore
            secret_key=settings.aws_secret_access_key,  # type: ignore
        )

    elif provider == "gcs":
        # Lazy import to avoid requiring google-cloud-storage if not using GCS
        from ai_commerce_gateway.storage.gcs import GCSStorageService

        if not settings.storage_bucket:
            raise ValueError("GCS storage requires: STORAGE_BUCKET")

        return GCSStorageService(
            bucket=settings.storage_bucket,
            credentials_json=settings.gcp_credentials_json.get_secret_value()
            if settings.gcp_credentials_json
            else None,
        )

    elif provider == "supabase":
        # Lazy import for Supabase storage
        from ai_commerce_gateway.storage.supabase import SupabaseStorageService

        if not all([settings.supabase_url, settings.supabase_service_role_key]):
            raise ValueError("Supabase storage requires: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY")

        return SupabaseStorageService(
            project_url=settings.supabase_url,  # type: ignore
            service_role_key=settings.supabase_service_role_key.get_secret_value(),  # type: ignore
            bucket=settings.storage_bucket,
        )

    else:
        # unconfigured or unknown provider
        return None
