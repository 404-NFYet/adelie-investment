"""MinIO (S3-compatible) service for PDF storage."""

import io
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False


class MinIOService:
    """Service for interacting with MinIO storage."""
    
    BUCKET_REPORTS = "naver-reports"
    BUCKET_EXTRACTED = "extracted-data"
    
    def __init__(self):
        """Initialize MinIO client."""
        if not MINIO_AVAILABLE:
            raise ImportError("minio package is not installed. Run: pip install minio")
        
        self.endpoint = os.getenv("MINIO_ENDPOINT", "10.10.10.10:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )
        
        self._ensure_buckets()
    
    def _ensure_buckets(self):
        """Ensure required buckets exist."""
        buckets = [self.BUCKET_REPORTS, self.BUCKET_EXTRACTED]
        
        for bucket in buckets:
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    print(f"✅ Created bucket: {bucket}")
            except S3Error as e:
                print(f"⚠️ Error checking/creating bucket {bucket}: {e}")
    
    def upload_pdf(
        self,
        file_path: str,
        object_name: Optional[str] = None,
        bucket: Optional[str] = None,
    ) -> str:
        """
        Upload a PDF file to MinIO.
        
        Args:
            file_path: Local path to the PDF file
            object_name: Object name in MinIO (defaults to filename)
            bucket: Target bucket (defaults to BUCKET_REPORTS)
            
        Returns:
            Object name (path in MinIO)
        """
        bucket = bucket or self.BUCKET_REPORTS
        
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if object_name is None:
            # Create object name with date prefix
            date_prefix = datetime.now().strftime("%Y/%m/%d")
            object_name = f"{date_prefix}/{path.name}"
        
        try:
            self.client.fput_object(
                bucket,
                object_name,
                str(path),
                content_type="application/pdf",
            )
            print(f"✅ Uploaded: {object_name}")
            return object_name
        except S3Error as e:
            print(f"❌ Upload failed: {e}")
            raise
    
    def upload_bytes(
        self,
        data: bytes,
        object_name: str,
        bucket: Optional[str] = None,
        content_type: str = "application/pdf",
    ) -> str:
        """
        Upload bytes data to MinIO.
        
        Args:
            data: Bytes data to upload
            object_name: Object name in MinIO
            bucket: Target bucket
            content_type: MIME type
            
        Returns:
            Object name
        """
        bucket = bucket or self.BUCKET_REPORTS
        
        try:
            self.client.put_object(
                bucket,
                object_name,
                io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
            print(f"✅ Uploaded: {object_name} ({len(data)} bytes)")
            return object_name
        except S3Error as e:
            print(f"❌ Upload failed: {e}")
            raise
    
    def download_pdf(
        self,
        object_name: str,
        bucket: Optional[str] = None,
    ) -> bytes:
        """
        Download a PDF file from MinIO.
        
        Args:
            object_name: Object name in MinIO
            bucket: Source bucket
            
        Returns:
            PDF file content as bytes
        """
        bucket = bucket or self.BUCKET_REPORTS
        
        try:
            response = self.client.get_object(bucket, object_name)
            return response.read()
        except S3Error as e:
            print(f"❌ Download failed: {e}")
            raise
        finally:
            if 'response' in locals():
                response.close()
                response.release_conn()
    
    def list_pdfs(
        self,
        prefix: Optional[str] = None,
        bucket: Optional[str] = None,
    ) -> list[dict]:
        """
        List PDF files in MinIO.
        
        Args:
            prefix: Optional prefix filter
            bucket: Target bucket
            
        Returns:
            List of object info dictionaries
        """
        bucket = bucket or self.BUCKET_REPORTS
        
        try:
            objects = self.client.list_objects(bucket, prefix=prefix, recursive=True)
            return [
                {
                    "name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                }
                for obj in objects
                if obj.object_name.endswith(".pdf")
            ]
        except S3Error as e:
            print(f"❌ List failed: {e}")
            raise
    
    def delete_pdf(
        self,
        object_name: str,
        bucket: Optional[str] = None,
    ) -> bool:
        """
        Delete a PDF file from MinIO.
        
        Args:
            object_name: Object name in MinIO
            bucket: Target bucket
            
        Returns:
            True if deleted successfully
        """
        bucket = bucket or self.BUCKET_REPORTS
        
        try:
            self.client.remove_object(bucket, object_name)
            print(f"✅ Deleted: {object_name}")
            return True
        except S3Error as e:
            print(f"❌ Delete failed: {e}")
            return False
    
    def get_presigned_url(
        self,
        object_name: str,
        bucket: Optional[str] = None,
        expires: int = 3600,
    ) -> str:
        """
        Get a presigned URL for downloading a PDF.
        
        Args:
            object_name: Object name in MinIO
            bucket: Target bucket
            expires: URL expiration in seconds
            
        Returns:
            Presigned URL
        """
        from datetime import timedelta
        
        bucket = bucket or self.BUCKET_REPORTS
        
        try:
            url = self.client.presigned_get_object(
                bucket,
                object_name,
                expires=timedelta(seconds=expires),
            )
            return url
        except S3Error as e:
            print(f"❌ Presigned URL failed: {e}")
            raise


# Singleton instance (lazy initialization)
_minio_service: Optional[MinIOService] = None


def get_minio_service() -> MinIOService:
    """Get MinIO service instance."""
    global _minio_service
    if _minio_service is None:
        _minio_service = MinIOService()
    return _minio_service


# Test function
def test_minio_connection():
    """Test MinIO connection."""
    try:
        service = get_minio_service()
        print("✅ MinIO connection successful")
        print(f"   Endpoint: {service.endpoint}")
        
        # List buckets
        buckets = service.client.list_buckets()
        print(f"   Buckets: {[b.name for b in buckets]}")
        
        return True
    except Exception as e:
        print(f"❌ MinIO connection failed: {e}")
        return False


if __name__ == "__main__":
    test_minio_connection()
